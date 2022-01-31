"""Table definitions for the FERC Form 1 data group."""
from typing import Any, Dict

from pudl.metadata.codes import CODE_METADATA

RESOURCE_METADATA: Dict[str, Dict[str, Any]] = {
    "accumulated_depreciation_ferc1": {
        "description": "Balances and changes to FERC Accumulated Provision for Depreciation.",
        "schema": {
            "fields": [
                "utility_id_ferc1",
                "report_year",
                "record_id",
                "line_id",
                "total",
                "electric_plant",
                "future_plant",
                "leased_plant",
            ],
            "primary_key": ["utility_id_ferc1", "report_year", "line_id"],
        },
        "sources": ["ferc1"],
        "etl_group": "ferc1",
        "field_namespace": "ferc1"
    },
    "ferc_accounts": {
        "description": "Account numbers from the FERC Uniform System of Accounts for Electric Plant, which is defined in Code of Federal Regulations (CFR) Title 18, Chapter I, Subchapter C, Part 101. (See e.g. https://www.law.cornell.edu/cfr/text/18/part-101).",
        "schema": {
            "fields": ["ferc_account_id", "ferc_account_description"],
            "primary_key": ["ferc_account_id"],
        },
        "sources": ["ferc1"],
        "etl_group": "static",
        "field_namespace": "ferc1"
    },
    "ferc_depreciation_lines": {
        "description": "PUDL assigned FERC Form 1 line identifiers and long descriptions from FERC Form 1 page 219, Accumulated Provision for Depreciation of Electric Utility Plant (Account 108).",
        "schema": {
            "fields": ["line_id", "ferc_account_description"],
            "primary_key": ["line_id"],
            "foreign_key_rules": {"fields": [["line_id"]]},
        },
        "sources": ["ferc1"],
        "etl_group": "static",
        "field_namespace": "ferc1"
    },
    "fuel_ferc1": {
        "description": "Annual fuel cost and quanitiy for steam plants with a capacity of 25+ MW, internal combustion and gas-turbine plants of 10+ MW, and all nuclear plants. As reported on page 402 of FERC Form 1 and extracted from the f1_fuel table in FERC's FoxPro Database.",
        "schema": {
            "fields": [
                "record_id",
                "utility_id_ferc1",
                "report_year",
                "plant_name_ferc1",
                "fuel_type_code_pudl",
                "fuel_units",
                "fuel_consumed_units",
                "fuel_mmbtu_per_unit",
                "fuel_cost_per_unit_burned",
                "fuel_cost_per_unit_delivered",
                "fuel_cost_per_mmbtu",
            ],
        },
        "sources": ["ferc1"],
        "etl_group": "ferc1",
        "field_namespace": "ferc1"
    },
    "plant_in_service_ferc1": {
        "description": "Balances and changes to FERC Electric Plant in Service accounts, as reported on FERC Form 1. Data originally from the f1_plant_in_srvce table in FERC's FoxPro database. Account numbers correspond to the FERC Uniform System of Accounts for Electric Plant, which is defined in Code of Federal Regulations (CFR) Title 18, Chapter I, Subchapter C, Part 101. (See e.g. https://www.law.cornell.edu/cfr/text/18/part-101). Each FERC respondent reports starting and ending balances for each account annually. Balances are organization wide, and are not broken down on a per-plant basis. End of year balance should equal beginning year balance plus the sum of additions, retirements, adjustments, and transfers.",
        "schema": {
            "fields": [
                "utility_id_ferc1",
                "report_year",
                "amount_type",
                "record_id",
                "distribution_acct360_land",
                "distribution_acct361_structures",
                "distribution_acct362_station_equip",
                "distribution_acct363_storage_battery_equip",
                "distribution_acct364_poles_towers",
                "distribution_acct365_overhead_conductors",
                "distribution_acct366_underground_conduit",
                "distribution_acct367_underground_conductors",
                "distribution_acct368_line_transformers",
                "distribution_acct369_services",
                "distribution_acct370_meters",
                "distribution_acct371_customer_installations",
                "distribution_acct372_leased_property",
                "distribution_acct373_street_lighting",
                "distribution_acct374_asset_retirement",
                "distribution_total",
                "electric_plant_in_service_total",
                "electric_plant_purchased_acct102",
                "electric_plant_sold_acct102",
                "experimental_plant_acct103",
                "general_acct389_land",
                "general_acct390_structures",
                "general_acct391_office_equip",
                "general_acct392_transportation_equip",
                "general_acct393_stores_equip",
                "general_acct394_shop_equip",
                "general_acct395_lab_equip",
                "general_acct396_power_operated_equip",
                "general_acct397_communication_equip",
                "general_acct398_misc_equip",
                "general_acct399_1_asset_retirement",
                "general_acct399_other_property",
                "general_subtotal",
                "general_total",
                "hydro_acct330_land",
                "hydro_acct331_structures",
                "hydro_acct332_reservoirs_dams_waterways",
                "hydro_acct333_wheels_turbines_generators",
                "hydro_acct334_accessory_equip",
                "hydro_acct335_misc_equip",
                "hydro_acct336_roads_railroads_bridges",
                "hydro_acct337_asset_retirement",
                "hydro_total",
                "intangible_acct301_organization",
                "intangible_acct302_franchises_consents",
                "intangible_acct303_misc",
                "intangible_total",
                "major_electric_plant_acct101_acct106_total",
                "nuclear_acct320_land",
                "nuclear_acct321_structures",
                "nuclear_acct322_reactor_equip",
                "nuclear_acct323_turbogenerators",
                "nuclear_acct324_accessory_equip",
                "nuclear_acct325_misc_equip",
                "nuclear_acct326_asset_retirement",
                "nuclear_total",
                "other_acct340_land",
                "other_acct341_structures",
                "other_acct342_fuel_accessories",
                "other_acct343_prime_movers",
                "other_acct344_generators",
                "other_acct345_accessory_equip",
                "other_acct346_misc_equip",
                "other_acct347_asset_retirement",
                "other_total",
                "production_total",
                "rtmo_acct380_land",
                "rtmo_acct381_structures",
                "rtmo_acct382_computer_hardware",
                "rtmo_acct383_computer_software",
                "rtmo_acct384_communication_equip",
                "rtmo_acct385_misc_equip",
                "rtmo_total",
                "steam_acct310_land",
                "steam_acct311_structures",
                "steam_acct312_boiler_equip",
                "steam_acct313_engines",
                "steam_acct314_turbogenerators",
                "steam_acct315_accessory_equip",
                "steam_acct316_misc_equip",
                "steam_acct317_asset_retirement",
                "steam_total",
                "transmission_acct350_land",
                "transmission_acct352_structures",
                "transmission_acct353_station_equip",
                "transmission_acct354_towers",
                "transmission_acct355_poles",
                "transmission_acct356_overhead_conductors",
                "transmission_acct357_underground_conduit",
                "transmission_acct358_underground_conductors",
                "transmission_acct359_1_asset_retirement",
                "transmission_acct359_roads_trails",
                "transmission_total",
            ],
            "primary_key": ["utility_id_ferc1", "report_year", "amount_type"],
        },
        "sources": ["ferc1"],
        "etl_group": "ferc1",
        "field_namespace": "ferc1"
    },
    "plants_ferc1": {
        "description": "FERC 1 Plants and their associated manually assigned PUDL Plant IDs",
        "schema": {
            "fields": ["utility_id_ferc1", "plant_name_ferc1", "plant_id_pudl"],
            "primary_key": ["utility_id_ferc1", "plant_name_ferc1"],
            "foreign_key_rules": {
                "fields": [
                    ["utility_id_ferc1", "plant_name_ferc1"],
                ],
            },
        },
        "sources": ["ferc1"],
        "etl_group": "glue",
        "field_namespace": "ferc1"
    },
    "plants_hydro_ferc1": {
        "description": "Hydroelectric generating plant statistics for large plants. Large plants have an installed nameplate capacity of more than 10 MW. As reported on FERC Form 1, pages 406-407, and extracted from the f1_hydro table in FERC's FoxPro database.",
        "schema": {
            "fields": [
                "record_id",
                "utility_id_ferc1",
                "report_year",
                "plant_name_ferc1",
                "project_num",
                "plant_type",
                "construction_type",
                "construction_year",
                "installation_year",
                "capacity_mw",
                "peak_demand_mw",
                "plant_hours_connected_while_generating",
                "net_capacity_favorable_conditions_mw",
                "net_capacity_adverse_conditions_mw",
                "avg_num_employees",
                "net_generation_mwh",
                "capex_land",
                "capex_structures",
                "capex_facilities",
                "capex_equipment",
                "capex_roads",
                "asset_retirement_cost",
                "capex_total",
                "capex_per_mw",
                "opex_operations",
                "opex_water_for_power",
                "opex_hydraulic",
                "opex_electric",
                "opex_generation_misc",
                "opex_rents",
                "opex_engineering",
                "opex_structures",
                "opex_dams",
                "opex_plant",
                "opex_misc_plant",
                "opex_total",
                "opex_per_mwh",
            ],
        },
        "sources": ["ferc1"],
        "etl_group": "ferc1",
        "field_namespace": "ferc1"
    },
    "plants_pumped_storage_ferc1": {
        "description": "Generating plant statistics for hydroelectric pumped storage plants with an installed nameplate capacity of 10+ MW. As reported on page 408 of FERC Form 1 and extracted from the f1_pumped_storage table in FERC's FoxPro Database.",
        "schema": {
            "fields": [
                "record_id",
                "utility_id_ferc1",
                "report_year",
                "plant_name_ferc1",
                "project_num",
                "construction_type",
                "construction_year",
                "installation_year",
                "capacity_mw",
                "peak_demand_mw",
                "plant_hours_connected_while_generating",
                "plant_capability_mw",
                "avg_num_employees",
                "net_generation_mwh",
                "energy_used_for_pumping_mwh",
                "net_load_mwh",
                "capex_land",
                "capex_structures",
                "capex_facilities",
                "capex_wheels_turbines_generators",
                "capex_equipment_electric",
                "capex_equipment_misc",
                "capex_roads",
                "asset_retirement_cost",
                "capex_total",
                "capex_per_mw",
                "opex_operations",
                "opex_water_for_power",
                "opex_pumped_storage",
                "opex_electric",
                "opex_generation_misc",
                "opex_rents",
                "opex_engineering",
                "opex_structures",
                "opex_dams",
                "opex_plant",
                "opex_misc_plant",
                "opex_production_before_pumping",
                "opex_pumping",
                "opex_total",
                "opex_per_mwh",
            ],
        },
        "sources": ["ferc1"],
        "etl_group": "ferc1",
        "field_namespace": "ferc1"
    },
    "plants_small_ferc1": {
        "description": "Generating plant statistics for steam plants with less than 25 MW installed nameplate capacity and internal combustion plants, gas turbine-plants, conventional hydro plants, and pumped storage plants with less than 10 MW installed nameplate capacity. As reported on FERC Form 1 pages 410-411, and extracted from the FERC FoxPro database table f1_gnrt_plant.",
        "schema": {
            "fields": [
                "record_id",
                "utility_id_ferc1",
                "report_year",
                "plant_name_clean",
                "plant_name_ferc1",
                "plant_type",
                "ferc_license_id",
                "construction_year",
                "capacity_mw",
                "peak_demand_mw",
                "net_generation_mwh",
                "total_cost_of_plant",
                "capex_per_mw",
                "opex_total",
                "opex_fuel",
                "opex_maintenance",
                "fuel_type",
                "fuel_cost_per_mmbtu",
            ],
        },
        "sources": ["ferc1"],
        "etl_group": "ferc1",
        "field_namespace": "ferc1"
    },
    "plants_steam_ferc1": {
        "description": "Generating plant statistics for steam plants with a capacity of 25+ MW, internal combustion and gas-turbine plants of 10+ MW, and all nuclear plants. As reported on page 402 of FERC Form 1 and extracted from the f1_gnrt_plant table in FERC's FoxPro Database.",
        "schema": {
            "fields": [
                "record_id",
                "utility_id_ferc1",
                "report_year",
                "plant_id_ferc1",
                "plant_name_ferc1",
                "plant_type",
                "construction_type",
                "construction_year",
                "installation_year",
                "capacity_mw",
                "peak_demand_mw",
                "plant_hours_connected_while_generating",
                "plant_capability_mw",
                "water_limited_capacity_mw",
                "not_water_limited_capacity_mw",
                "avg_num_employees",
                "net_generation_mwh",
                "capex_land",
                "capex_structures",
                "capex_equipment",
                "capex_total",
                "capex_per_mw",
                "opex_operations",
                "opex_fuel",
                "opex_coolants",
                "opex_steam",
                "opex_steam_other",
                "opex_transfer",
                "opex_electric",
                "opex_misc_power",
                "opex_rents",
                "opex_allowances",
                "opex_engineering",
                "opex_structures",
                "opex_boiler",
                "opex_plants",
                "opex_misc_steam",
                "opex_production_total",
                "opex_per_mwh",
                "asset_retirement_cost",
            ],
        },
        "sources": ["ferc1"],
        "etl_group": "ferc1",
        "field_namespace": "ferc1"
    },
    "power_purchase_types_ferc1": {
        "description": "Coding table defining different types of electricity power purchases.",
        "schema": {
            "fields": ["code", "label", "description"],
            "primary_key": ["code"],
            "foreign_key_rules": {"fields": [["purchase_type_code"]]},
        },
        "encoder": CODE_METADATA["power_purchase_types_ferc1"],
        "sources": ["ferc1"],
        "etl_group": "static",
        "field_namespace": "ferc1"
    },
    "purchased_power_ferc1": {
        "description": "Purchased Power (Account 555) including power exchanges (i.e. transactions involving a balancing of debits and credits for energy, capacity, etc.) and any settlements for imbalanced exchanges. Reported on pages 326-327 of FERC Form 1. Extracted from the f1_purchased_pwr table in FERC's FoxPro database.",
        "schema": {
            "fields": [
                "record_id",
                "utility_id_ferc1",
                "report_year",
                "seller_name",
                "purchase_type_code",
                "tariff",
                "billing_demand_mw",
                "non_coincident_peak_demand_mw",
                "coincident_peak_demand_mw",
                "purchased_mwh",
                "received_mwh",
                "delivered_mwh",
                "demand_charges",
                "energy_charges",
                "other_charges",
                "total_settlement",
            ]
        },
        "sources": ["ferc1"],
        "etl_group": "ferc1",
        "field_namespace": "ferc1"
    },
    "utilities_ferc1": {
        "description": "This table maps the manually assigned PUDL utility ID to a FERC respondent ID, enabling a connection between the FERC and EIA data sets. It also stores the utility name associated with the FERC respondent ID. Those values originate in the f1_respondent_id table in FERC's FoxPro database, which is stored in a file called F1_1.DBF. This table is generated from a spreadsheet stored in the PUDL repository: src/package_data/glue/pudl_id_mapping.xlsx",
        "schema": {
            "fields": ["utility_id_ferc1", "utility_name_ferc1", "utility_id_pudl"],
            "primary_key": ["utility_id_ferc1"],
            "foreign_key_rules": {"fields": [["utility_id_ferc1"]]},
        },
        "sources": ["ferc1"],
        "etl_group": "glue",
        "field_namespace": "ferc1"
    },
}
"""
FERC Form 1 resource attributes by PUDL identifier (``resource.name``).

Keys are in alphabetical order.

See :func:`pudl.metadata.helpers.build_foreign_keys` for the expected format of
``foreign_key_rules``.
"""
