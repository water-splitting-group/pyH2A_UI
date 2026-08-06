# Input files to merge

Name | Value
--- | ---
Default TEA | pyH2A.Config~Defaults_TEA.md

# Workflow

Name | Position
--- | ---

# Functional Unit

Name | Unit
--- | ---
Functional Unit | kg

# Display Parameters

Name | Value
--- | ---
Name | New pathway
Color | darkblue

# Construction

Name | Value | Unit | Comment
--- | --- | --- | ---
Capital spent in 1st year of construction | 100% | - | Split this across several rows for a multi-year build

# Technical Operating Parameters and Specifications

Name | Value | Unit | Comment
--- | --- | --- | ---
Plant design capacity | 1000 | kg/day | What the plant is built to make
Operating capacity factor | 90% | - | Fraction of the year it actually runs
Fraction of output that reaches gate | 100% | - | Losses between production and sale

# Direct Capital Costs - Plant

Name | Value | Unit | Comment
--- | --- | --- | ---
Plant | 1000000 | USD | Replace with the equipment your pathway actually buys

# Non-Depreciable Capital Costs

Name | Value | Unit
--- | --- | ---
Cost of land | 500 | USD/acre
Land required | 1 | acre

# Fixed Operating Costs

Name | Value | Unit | Comment
--- | --- | --- | ---
Staff | 5 | - | Full-time equivalents
Hourly labor cost | 50 | USD/h | Burdened, including overhead

# Other Fixed Operating Costs

Name | Value | Path | Unit | Comment
--- | --- | --- | --- | ---
Maintenance | 2% | {Direct Capital Costs - Plant > Plant > Value, USD} | USD | A fraction of what the plant cost

# Planned Replacement

Name | Cost_Value | Cost_Unit | Frequency_Value | Frequency_Unit
--- | --- | --- | --- | ---

# Utilities

Name | Usage_Value | Usage_Unit | Cost_Value | Cost_Unit | Price_Conversion_Factor_Value | Price_Conversion_Factor_Unit
--- | --- | --- | --- | --- | --- | ---
Electricity | 50 | 1/kg | 0.07 | USD | 1. | -
