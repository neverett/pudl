"""
Allocate data from generation_fuel_eia923 table to generator level.

Net electricity generation and fuel consumption are reported in mutiple ways
in the EIA 923. The generation_fuel_eia923 table reports both generation and
fuel consumption, and breaks them down by plant, prime mover, and fuel. In
parallel, the generation_eia923 table reports generation by generator, and the
boiler_fuel_eia923 table reports fuel consumption by boiler.

The generation_fuel_eia923 table is more complete, but the generation_eia923 +
boiler_fuel_eia923 tables are more granular. The generation_eia923 table
includes only ~55% of the total MWhs reported in the generation_fuel_eia923
table.

This module estimates the net electricity generation and fuel consumption
attributable to individual generators based on the more expansive reporting of
the data in the generation_fuel_eia923 table. The main coordinating function
here is :func:`pudl.analysis.allocate_net_gen.allocate_gen_fuel_by_gen`.

The algorithm we're using assumes:

* The generation_eia923 table is the authoritative source of information about
  how much generation is attributable to an individual generator, if it reports
  in that table.
* The generation_fuel_eia923 table is the authoritative source of information
  about how much generation and fuel consumption is attributable to an entire
  plant.
* The generators_eia860 table provides an exhaustive list of all generators
  whose generation is being reported in the generation_fuel_eia923 table.

We allocate the net generation reported in the generation_fuel_eia923 table on
the basis of plant, prime mover, and fuel type among the generators in each
plant that have matching fuel types. Generation is allocated proportional to
reported generation if it's available, and proportional to each generator's
capacity if generation is not available.

In more detail: within each year of data, we split the plants into three groups:

* Plants where ALL generators report in the more granular generation_eia923
  table.
* Plants where NONE of the generators report in the generation_eia923 table.
* Plants where only SOME of the generators report in the generation_eia923
  table.

In plant-years where ALL generators report more granular generation, the total
net generation reported in the generation_fuel_eia923 table is allocated in
proportion to the generation each generator reported in the generation_eia923
table. We do this instead of using net_generation_mwh from generation_eia923
because there are some small discrepancies between the total amounts of
generation reported in these two tables.

In plant-years where NONE of the generators report more granular generation,
we create a generator record for each associated fuel type. Those records are
merged with the generation_fuel_eia923 table on plant, prime mover code, and
fuel type. Each group of plant, prime mover, and fuel will have some amount of
reported net generation associated with it, and one or more generators. The
net generation is allocated among the generators within the group in proportion
to their capacity. Then the allocated net generation is summed up by generator.

In the hybrid case, where only SOME of of a plant's generators report the more
granular generation data, we use a combination of the two allocation methods
described above. First, the total generation reported across a plant in the
generation_fuel_eia923 table is allocated between the two categories of
generators (those that report fine-grained generation, and those that don't)
in direct proportion to the fraction of the plant's generation which is reported
in the generation_eia923 table, relative to the total generation reported in the
generation_fuel_eia923 table.

Note that this methology does not distinguish between primary and secondary
fuel_types for generators. It associates portions of net generation to each
combination of prime_mover_code and fuel_type equally. In cases where two
generators in the same plant do not report detailed generation, have the same
prime_mover_code, and use the same fuels, but have very different capacity
factors in reality, this methodology will allocate generation such that they
end up with very similar capacity factors. We imagine this is an uncommon
scenario.

This methodology has several potential flaws and drawbacks. Because there is no
indicator of what portion of the energy_source_codes (ie. fuel_type), we
associate the net generation equally among them. In effect, if a plant had
multiple generators with the same prime_mover_code but opposite primary and
secondary fuels (eg. gen 1 has a primary fuel of 'NG' and secondary fuel of
'DFO', while gen 2 has a primary fuel of 'DFO' and a secondary fuel of 'NG'),
the methodology associates the generation_fuel_eia923 records similarly across
these two generators. However, the allocated net generation will still be
porporational to each generator's net generation (if it's reported) or capacity
(if generation is not reported).

"""

import logging
import warnings

# Useful high-level external modules.
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

IDX_GENS = ['plant_id_eia', 'generator_id', 'report_date']
"""Id columns for generators."""

IDX_PM_FUEL = ['plant_id_eia', 'prime_mover_code',
               'fuel_type', 'report_date']
"""Id columns for plant, prime mover & fuel type records."""

IDX_FUEL = ['report_date', 'plant_id_eia', 'fuel_type']

DATA_COLS = ['net_generation_mwh', 'fuel_consumed_mmbtu']
"""Data columns from generation_fuel_eia923 that are being allocated."""


def allocate_gen_fuel_by_gen(pudl_out):
    """
    Allocate gen fuel data columns to generators.

    The generation_fuel_eia923 table includes net generation and fuel
    consumption data at the plant/fuel type/prime mover level. The most
    granular level of plants that PUDL typically uses is at the plant/generator
    level. This method converts the generation_fuel_eia923 table to the level
    of plant/generators.

    Args:
        pudl_out (pudl.output.pudltabl.PudlTabl): An object used to create
            the tables for EIA and FERC Form 1 analysis.

    Returns:
        pandas.DataFrame: table with columns ``IDX_GENS`` and ``DATA_COLS``.
        The ``DATA_COLS`` will be scaled to the level of the ``IDX_GENS``.

    """
    gen_pm_fuel = allocate_gen_fuel_by_gen_pm_fuel(pudl_out)
    gen = agg_by_generator(gen_pm_fuel)
    _test_gen_fuel_allocation(pudl_out, gen)
    return gen


def allocate_gen_fuel_by_gen_pm_fuel(pudl_out):
    """
    Proportionally allocate net gen from gen_fuel table to generators.

    Two main steps here:
     * associate gen_fuel data w/ generators
     * allocate gen_fuel data proportionally

     The association process happens via `associate_gen_tables()`.

     The allocation process entails generating a ratio for each record within a
     ``IDX_PM_FUEL`` group. We have two options for generating this ratio: the
     net generation in the generation_eia923 table and the capacity from the
     generators_eia860 table. We calculate both these ratios, then used the
     net generation based ratio if available to allocation a portion of the
     associated data fields.

    Args:
        pudl_out (pudl.output.pudltabl.PudlTabl): An object used to create
            the tables for EIA and FERC Form 1 analysis.

    Returns:
        pandas.DataFrame
    """
    gens_asst = (
        associate_gen_tables(pudl_out)
        .pipe(_associate_unconnected_records)
        .pipe(_associate_fuel_type_only, pudl_out)
    )

    gen_pm_fuel = make_allocation_ratio(gens_asst, pudl_out)

    # do the allocating-ing!
    gen_pm_fuel = (
        gen_pm_fuel.assign(
            # we could x.net_generation_mwh_gen.fillna here if we wanted to
            # take the net gen
            net_generation_mwh=lambda x: x.net_generation_mwh_gf * x.gen_ratio,
            # let's preserve the gf version of fuel consumption (it didn't show
            # up in the tables we pulled together in associate_gen_tables()).
            fuel_consumed_mmbtu_gf=lambda x: x.fuel_consumed_mmbtu,
            fuel_consumed_mmbtu=lambda x: x.fuel_consumed_mmbtu * x.gen_ratio
        )
    )

    gen_pm_fuel = (
        gen_pm_fuel
        .astype(
            {"plant_id_eia": pd.Int64Dtype(),
             "net_generation_mwh": "float"})
        .dropna(how='all')
        .pipe(_test_gen_pm_fuel_output, pudl_out)
    )
    return gen_pm_fuel


def agg_by_generator(gen_pm_fuel):
    """
    Aggreate the allocated gen fuel data to the generator level.

    Args:
        gen_pm_fuel (pandas.DataFrame): result of
            `allocate_gen_fuel_by_gen_pm_fuel()`
    """
    data_cols = ['net_generation_mwh', 'fuel_consumed_mmbtu']
    gen = (gen_pm_fuel.groupby(by=IDX_GENS)
           [data_cols].sum(min_count=1).reset_index())

    return gen


def _stack_generators(pudl_out, idx_stack, cols_to_stack,
                      cat_col='energy_source_code_num',
                      stacked_col='fuel_type'):
    """
    Stack the generator table with a set of columns.

    Args:
        pudl_out (pudl.output.pudltabl.PudlTabl): An object used to create
            the tables for EIA and FERC Form 1 analysis.
        idx_stack (iterable): list of columns. index to stack based on
        cols_to_stack (iterable): list of columns to stack
        cat_col (string): name of category column which will end up having the
            column names of cols_to_stack
        stacked_col (string): name of column which will end up with the stacked
            data from cols_to_stack

    Returns:
        pandas.DataFrame: a dataframe with these columns: idx_stack, cat_col,
        stacked_col

    """
    gens = pudl_out.gens_eia860()
    gens_stack_prep = (
        pd.DataFrame(gens.set_index(idx_stack)[cols_to_stack].stack(level=0))
        .reset_index()
        .rename(columns={'level_3': cat_col, 0: stacked_col})
    )
    # merge the stacked df back onto the gens table
    # we first drop the cols_to_stack so we don't duplicate data
    gens_stack = pd.merge(
        gens.drop(columns=cols_to_stack),
        gens_stack_prep,
        how='outer'
    )
    return gens_stack


def associate_gen_tables(pudl_out):
    """
    Associate the three tables needed to assign net gen to generators.

    Args:
        pudl_out (pudl.output.pudltabl.PudlTabl): An object used to create
            the tables for EIA and FERC Form 1 analysis.
    """
    esc = [
        'energy_source_code_1', 'energy_source_code_2', 'energy_source_code_3',
        'energy_source_code_4', 'energy_source_code_5', 'energy_source_code_6'
    ]

    stack_gens = _stack_generators(
        pudl_out, idx_stack=IDX_GENS, cols_to_stack=esc,
        cat_col='energy_source_code_num', stacked_col='fuel_type')

    # because lots of these input dfs include same info columns, this generates
    # drop columnss for fuel_cost. This avoids needing to hard code columns.
    drop_cols_gens = [x for x in stack_gens.columns
                      if x in pudl_out.gen_original_eia923().columns
                      and x not in IDX_GENS]
    gens_asst = (
        pd.merge(
            stack_gens,
            pudl_out.gen_original_eia923().drop(columns=drop_cols_gens),
            on=IDX_GENS,
            how='outer')
        .merge(
            pudl_out.gf_eia923().groupby(by=IDX_PM_FUEL)
            .sum(min_count=1).reset_index(),
            on=IDX_PM_FUEL,
            suffixes=('_gen', '_gf'),
            how='outer',
        )
    )

    gens_asst = (
        pd.merge(
            gens_asst,
            gens_asst.groupby(by=IDX_FUEL)
            [['capacity_mw', 'net_generation_mwh_gen']].sum(min_count=1)
            .add_suffix('_fuel_total')
            .reset_index(),
            on=IDX_FUEL,
        )
    )
    return gens_asst


def _associate_unconnected_records(eia_generators_merged):
    """
    Associate unassociated gen_fuel table records on idx_pm.

    There are a subset of generation_fuel_eia923 records which do not
    merge onto the stacked generator table on ``IDX_PM_FUEL``. These records
    generally don't match with the set of prime movers and fuel types in the
    stacked generator table. In this method, we associate those straggler,
    unconnected records by merging these records with the stacked generators on
    the prime mover only.

    Args:
        eia_generators_merged (pandas.DataFrame)

    """
    # we're associating on the plant/pm level... but we only want to associated
    # these unassocaited records w/ the primary fuel type from _stack_generators
    # so we're going to merge on energy_source_code_num and
    idx_pm = ['plant_id_eia', 'prime_mover_code',
              'energy_source_code_num', 'report_date', ]
    # we're going to only associate these unconnected fuel records w/
    # the primary fuel so we don't have to deal w/ double counting
    connected_mask = eia_generators_merged.generator_id.notnull()
    eia_generators_connected = (
        eia_generators_merged[connected_mask]
    )
    eia_generators_unconnected = (
        eia_generators_merged[~connected_mask]
        .dropna(axis='columns', how='all')
        .rename(columns={'fuel_type': 'fuel_type_unconnected'})
        .assign(energy_source_code_num='energy_source_code_1')
        .groupby(by=idx_pm).sum(min_count=1)
        .reset_index()
    )

    eia_generators = (
        pd.merge(
            eia_generators_connected,
            eia_generators_unconnected[
                idx_pm + ['net_generation_mwh_gf', 'fuel_consumed_mmbtu']],
            on=idx_pm,
            suffixes=('', '_unconnected'),
            how='left'
        )
        .assign(
            # we want the main and the unconnected net gen to be added together
            # but sometimes there is no main net gen and sometimes there is no
            # unconnected net gen
            net_generation_mwh_gf=lambda x: np.where(
                x.net_generation_mwh_gf.notnull()
                | x.net_generation_mwh_gf_unconnected.notnull(),
                x.net_generation_mwh_gf.fillna(0)
                + x.net_generation_mwh_gf_unconnected.fillna(0),
                np.nan
            ),
            fuel_consumed_mmbtu=lambda x: np.where(
                x.fuel_consumed_mmbtu.notnull()
                | x.fuel_consumed_mmbtu_unconnected.notnull(),
                x.fuel_consumed_mmbtu.fillna(0)
                + x.fuel_consumed_mmbtu_unconnected.fillna(0),
                np.nan
            ),
        )
    )
    return eia_generators


def _associate_fuel_type_only(gens_asst, pudl_out):
    """
    Associate the records w/o prime movers with fuel cost.

    The 2001 and 2002 generation fuel table does not include any prime mover
    codes. Because of this, we need to associated these records via their fuel
    types.

    Note: 2001 and 2002 eia years are not currently integrated into PUDL.
    """
    # first fine the gf records that have no PM.
    gf_grouped = (
        pudl_out.gf_eia923()
        .groupby(by=IDX_PM_FUEL, dropna=False)
        .sum(min_count=1).reset_index()
    )
    gf_missing_pm = (
        gf_grouped[gf_grouped[IDX_PM_FUEL].isnull().any(axis=1)]
        .drop(columns=['prime_mover_code'])
        .set_index(IDX_FUEL).add_suffix("_fuel").reset_index()
    )

    gens_asst = pd.merge(
        gens_asst,
        gf_missing_pm,
        how='outer',
        on=IDX_FUEL,
        indicator=True
    )

    gens_asst = _associate_fuel_type_only_wo_matching_fuel_type(gens_asst)

    if gf_missing_pm.empty:
        logger.info(
            "No records found with fuel-only records. This is expected.")
    else:
        logger.info(
            f"{len(gf_missing_pm)/len(gens_asst):.02%} records w/o prime movers now"
            f" associated for: {gf_missing_pm.report_date.dt.year.unique()}")
    return gens_asst


def _associate_fuel_type_only_wo_matching_fuel_type(gens_asst):
    """
    Associate the missing-pm records that don't have matching fuel types.

    There are some generation fuel table records which don't associate with
    any of the energy_source_code's reported in for the generators. For these
    records, we need to take a step back and associate these records with the
    full plant.
    """
    idx_plant = ['plant_id_eia', 'report_date']
    gens_asst = pd.merge(
        gens_asst,
        gens_asst.groupby(by=idx_plant, dropna=False)[['capacity_mw']]
        .sum(min_count=1).add_suffix('_plant').reset_index(),
        on=idx_plant,
        how='left'
    )

    gens_asst_w_unassociated = (
        pd.merge(
            gens_asst[
                (gens_asst._merge != 'right_only')
                | (gens_asst._merge.isnull())
            ],
            (gens_asst[gens_asst._merge == 'right_only']
             .groupby(idx_plant)
             [['net_generation_mwh_fuel', 'fuel_consumed_mmbtu_fuel']]
             .sum(min_count=1)),
            on=idx_plant,
            how='left',
            suffixes=('', '_missing_pm')
        )
        .assign(
            net_generation_mwh_gf=lambda x:
                x.net_generation_mwh_gf.fillna(
                    x.net_generation_mwh_fuel
                    + x.net_generation_mwh_fuel_missing_pm.fillna(0)
                ),
            fuel_consumed_mmbtu=lambda x:
                x.fuel_consumed_mmbtu.fillna(
                    x.fuel_consumed_mmbtu_fuel
                    + x.fuel_consumed_mmbtu_fuel_missing_pm.fillna(0)
                ),
        )
    )
    return gens_asst_w_unassociated


def make_allocation_ratio(gens_asst, pudl_out):
    """
    Generate a ratio to use to allocate net generation by.

    The goal of  this function is to generation a column called `gen_ratio`,
    which will be a ratio to allocate net generation from the gf table from
    each `IDX_PM_FUEL` groups.
    """
    gen_pm_fuel = prep_alloction_ratio(gens_asst)
    gen_pm_fuel_ratio = calc_allocation_ratios(gen_pm_fuel, pudl_out)

    return gen_pm_fuel_ratio


def prep_alloction_ratio(gens_asst):
    """
    Make flags and aggregations to prepare for the `calc_allocation_ratios()`.

    In `calc_allocation_ratios()`, we will break the generators out into four
    types - see `calc_allocation_ratios()` docs for details. This function adds
    flags for splitting the generators. It also adds

    """
    # flag whether the generator exists in the
    # generation table (this will be used later on)
    # for calculating ratios to use to allocate net generation
    gens_asst = gens_asst.assign(
        exists_in_gen=lambda x: np.where(
            x.net_generation_mwh_gen.notnull(),
            True, False)
    )

    gens_gb = gens_asst.groupby(by=IDX_PM_FUEL)
    # get the total values for the merge group
    # we would use on groupby here with agg but it is much slower
    # so we're gb-ing twice w/ a merge
    # gens_gb.agg({'net_generation_mwh_gen': lambda x: x.sum(min_count=1),
    #              'capacity_mw': lambda x: x.sum(min_count=1),
    #              'exists_in_gen': 'all'},)
    gen_pm_fuel = (
        gens_asst
        .merge(  # flag if all generators exist in the generators_eia860 tbl
            gens_gb[['exists_in_gen']].all().reset_index(),
            on=IDX_PM_FUEL,
            suffixes=('', '_pm_fuel_total_all')
        )
        .merge(  # flag if some generators exist in the generators_eia860 tbl
            gens_gb[['exists_in_gen']].any().reset_index(),
            on=IDX_PM_FUEL,
            suffixes=('', '_pm_fuel_total_any')
        )
        # Net generation and capacity are both proxies that can be used
        # to allocate the generation which only shows up in generation_fuel
        # Sum them up across the whole plant-prime-fuel group so we can tell
        # what fraction of the total capacity each generator is.
        .merge(
            (gens_gb
             [['net_generation_mwh_gen', 'capacity_mw']]
             .sum(min_count=1)
             .add_suffix('_pm_fuel_total')
             .reset_index()),
            on=IDX_PM_FUEL,
        )
    )
    # Add a column that indicates how much capacity comes from generators that
    # report in the generation table, and how much comes only from generators
    # that show up in the generation_fuel table.
    gen_pm_fuel = (
        pd.merge(
            gen_pm_fuel,
            gen_pm_fuel.groupby(by=IDX_PM_FUEL + ['exists_in_gen'])
            [['capacity_mw']]
            .sum(min_count=1)
            .add_suffix('_exist_in_gen_group')
            .reset_index(),
            on=IDX_PM_FUEL + ['exists_in_gen'],
        )
    )
    return gen_pm_fuel


def calc_allocation_ratios(gen_pm_fuel, pudl_out):
    """
    Make `gen_ratio` column to allocate net gen from the generation fuel table.

    There are three main types of generators:
      * "all gen": generators of plants which fully report to the
        generators_eia860 table.
      * "some gen": generators of plants which partially report to the
        generators_eia860 table.
      * "gf only": generators of plants which do not report at all to the
        generators_eia860 table.
      * "no pm": generators that have missing prime movers.

    Each different type of generator needs to be treated slightly differently,
    but all will end up with a `gen_ratio` column that can be used to allocate
    the `net_generation_mwh_gf`.

    """
    # break out the table into these four different generator types.
    no_pm_mask = gen_pm_fuel.net_generation_mwh_fuel_missing_pm.notnull()
    no_pm = gen_pm_fuel[no_pm_mask]
    all_gen = gen_pm_fuel.loc[
        gen_pm_fuel.exists_in_gen_pm_fuel_total_all
        & ~no_pm_mask]
    some_gen = gen_pm_fuel.loc[
        gen_pm_fuel.exists_in_gen_pm_fuel_total_any
        & ~gen_pm_fuel.exists_in_gen_pm_fuel_total_all
        & ~no_pm_mask]
    gf_only = gen_pm_fuel.loc[
        ~gen_pm_fuel.exists_in_gen_pm_fuel_total_any
        & ~no_pm_mask]

    logger.info("Ratio calc types: \n"
                f"   All gens w/in generation table:  {len(all_gen)}\n"
                f"   Some gens w/in generation table: {len(some_gen)}\n"
                f"   No gens w/in generation table:   {len(gf_only)}\n"
                f"   GF table records have no PM:     {len(no_pm)}\n")
    if len(gen_pm_fuel) != len(all_gen) + len(some_gen) + len(gf_only) + len(no_pm):
        raise AssertionError(
            'Error in splitting the gens between records showing up fully, '
            'partially, or not at all in the generation table.'
        )

    # In the case where we have all of teh generation from the generation
    # table, we still allocate, because the generation reported in these two
    # tables don't always match perfectly
    all_gen = all_gen.assign(
        gen_ratio_net_gen=lambda x:
        x.net_generation_mwh_gen /
        x.net_generation_mwh_gen_pm_fuel_total,
        gen_ratio=lambda x:
            x.gen_ratio_net_gen
    )
    _ = _test_gen_ratio(all_gen, pudl_out)

    some_gen = some_gen.assign(
        gen_ratio_exist_in_gen_group=lambda x: x.net_generation_mwh_gen_pm_fuel_total /
        x.net_generation_mwh_gf,
        # for records within these mix groups that do have net gen in the
        # generation table..
        gen_ratio_net_gen=lambda x:
            x.net_generation_mwh_gen /
            x.net_generation_mwh_gen_pm_fuel_total,
        gen_ratio_net_gen_scaled_by_exist_portion=lambda x:
            x.gen_ratio_net_gen * x.gen_ratio_exist_in_gen_group,
        # when these records
        gen_ratio_remainder_exist_portion=lambda x:
            1 - x.gen_ratio_exist_in_gen_group,
        gen_ratio_remainder_by_cap=lambda x:
            x.gen_ratio_remainder_exist_portion * \
            (x.capacity_mw / x.capacity_mw_exist_in_gen_group),
        #
        gen_ratio=lambda x: np.where(
            x.net_generation_mwh_gen.notnull(),
            x.gen_ratio_net_gen_scaled_by_exist_portion,
            x.gen_ratio_remainder_by_cap)
    )
    _ = _test_gen_ratio(some_gen, pudl_out)

    # Calculate what fraction of the total capacity is associated with each of
    # the generators in the grouping.
    gf_only = gf_only.assign(
        gen_ratio_cap=lambda x:
            x.capacity_mw / x.capacity_mw_pm_fuel_total,
        gen_ratio=lambda x: x.gen_ratio_cap

    )
    _ = _test_gen_ratio(gf_only, pudl_out)

    no_pm = no_pm.assign(
        # ratio for the records with a missing prime mover that are
        # assocaited at the plant fuel level
        gen_ratio_net_gen_fuel=lambda x:
            x.net_generation_mwh_gf
            / x.net_generation_mwh_gen_fuel_total,
        gen_ratio_cap_fuel=lambda x:
            x.capacity_mw / x.capacity_mw_fuel_total,
        gen_ratio_fuel=lambda x:
            np.where(x.gen_ratio_net_gen_fuel.notnull()
                     | x.gen_ratio_net_gen_fuel != 0,
                     x.gen_ratio_net_gen_fuel, x.gen_ratio_cap_fuel),
        gen_ratio=lambda x: x.gen_ratio_fuel
    )

    # squish all of these methods back together.
    gen_pm_fuel_ratio = pd.concat([all_gen, some_gen, gf_only, no_pm])
    # null out the inf's
    gen_pm_fuel_ratio.loc[abs(gen_pm_fuel_ratio.gen_ratio) == np.inf] = np.NaN
    _ = _test_gen_ratio(gen_pm_fuel_ratio, pudl_out)
    return gen_pm_fuel_ratio


def _test_gen_ratio(gen_pm_fuel, pudl_out):
    # test! Check if each of the IDX_PM_FUEL groups gen_ratio's add up to 1
    ratio_test_pm_fuel = (
        gen_pm_fuel.groupby(IDX_PM_FUEL)
        [['gen_ratio', 'net_generation_mwh_gen']].sum(min_count=1)
        .reset_index()
    )

    ratio_test_fuel = (
        gen_pm_fuel.groupby(IDX_FUEL)
        [['gen_ratio', 'net_generation_mwh_fuel']].sum(min_count=1)
        .reset_index()
    )

    ratio_test = (
        pd.merge(
            ratio_test_pm_fuel, ratio_test_fuel,
            on=IDX_FUEL,
            suffixes=("", "_fuel")
        )
        .assign(
            gen_ratio_pm_fuel=lambda x: x.gen_ratio,
            gen_ratio=lambda x: np.where(
                x.gen_ratio_pm_fuel.notnull(),
                x.gen_ratio_pm_fuel, x.gen_ratio_fuel,
            )
        )
    )

    ratio_test_bad = ratio_test[
        ~np.isclose(ratio_test.gen_ratio, 1)
        & ratio_test.gen_ratio.notnull()
    ]
    if not ratio_test_bad.empty:
        pudl_out.ratio_test = ratio_test
        pudl_out.ratio_test_bad = ratio_test_bad
        # raise AssertionError(
        warnings.warn(
            f"Ooopsies. You got {len(ratio_test_bad)} records where the "
            "'gen_ratio' column isn't adding up to 1 for each 'IDX_PM_FUEL' "
            "group. Check 'make_allocation_ratio()'"
        )
    return ratio_test_bad


def _test_gen_pm_fuel_output(gen_pm_fuel, pudl_out):
    # this is just for testing/debugging
    def calc_net_gen_diff(gen_pm_fuel, idx):
        gen_pm_fuel_test = (
            pd.merge(
                gen_pm_fuel,
                gen_pm_fuel.groupby(by=idx)
                [['net_generation_mwh']]
                .sum(min_count=1).add_suffix('_test').reset_index(),
                on=idx,
                how='outer'
            )
            .assign(net_generation_mwh_diff=lambda x:
                    x.net_generation_mwh_gf
                    - x.net_generation_mwh_test)
        )
        return gen_pm_fuel_test
    # make different totals and calc differences for two different indexs
    gen_pm_fuel_test = calc_net_gen_diff(gen_pm_fuel, idx=IDX_PM_FUEL)
    gen_fuel_test = calc_net_gen_diff(gen_pm_fuel, idx=IDX_FUEL)

    gen_pm_fuel_test = gen_pm_fuel_test.assign(
        net_generation_mwh_test=lambda x: x.net_generation_mwh_test.fillna(
            gen_fuel_test.net_generation_mwh_test),
        net_generation_mwh_diff=lambda x: x.net_generation_mwh_diff.fillna(
            gen_fuel_test.net_generation_mwh_diff),
    )

    bad_diff = gen_pm_fuel_test[
        (~np.isclose(gen_pm_fuel_test.net_generation_mwh_diff, 0))
        & (gen_pm_fuel_test.net_generation_mwh_diff.notnull())]
    logger.info(
        f"{len(bad_diff)/len(gen_pm_fuel):.03%} of records have are partially "
        "off from their 'IDX_PM_FUEL' group")
    no_cap_gen = gen_pm_fuel_test[
        (gen_pm_fuel_test.capacity_mw.isnull())
        & (gen_pm_fuel_test.net_generation_mwh_gen.isnull())
    ]
    if len(no_cap_gen) > 15:
        logger.info(
            f'Warning: {len(no_cap_gen)} records have no capacity or net gen')
    gen_fuel = pudl_out.gf_eia923()
    gen = pudl_out.gen_original_eia923()
    # remove the junk/corrective plants
    fuel_net_gen = gen_fuel[
        gen_fuel.plant_id_eia != '99999'].net_generation_mwh.sum()
    fuel_consumed = gen_fuel[
        gen_fuel.plant_id_eia != '99999'].fuel_consumed_mmbtu.sum()
    logger.info(
        "gen v fuel table net gen diff:      "
        f"{(gen.net_generation_mwh.sum())/fuel_net_gen:.1%}")
    logger.info(
        "new v fuel table net gen diff:      "
        f"{(gen_pm_fuel_test.net_generation_mwh.sum())/fuel_net_gen:.1%}")
    logger.info(
        "new v fuel table fuel (mmbtu) diff: "
        f"{(gen_pm_fuel_test.fuel_consumed_mmbtu.sum())/fuel_consumed:.1%}")
    return gen_pm_fuel_test


def _test_gen_fuel_allocation(pudl_out, gen_allocated, ratio=.05):
    gens_test = (
        pd.merge(
            gen_allocated,
            pudl_out.gen_original_eia923(),
            on=IDX_GENS,
            suffixes=('_new', '_og')
        )
        .assign(
            net_generation_new_v_og=lambda x:
                x.net_generation_mwh_new / x.net_generation_mwh_og)
    )

    os_ratios = gens_test[
        (~gens_test.net_generation_new_v_og.between((1 - ratio), (1 + ratio)))
        & (gens_test.net_generation_new_v_og.notnull())
    ]
    os_ratio = len(os_ratios) / len(gens_test)
    logger.info(
        f"{os_ratio:.2%} of generator records are more that {ratio:.0%} off from the net generation table")
    if ratio == 0.05 and os_ratio > .15:
        warnings.warn(
            f"Many generator records that have allocated net gen more than {ratio:.0%}"
        )
