"""The time wall (PLAN 5.1 and 9.5): the clock, the availability rules, and World.view(t).

An agent sees the world only through `world.view.View`, which holds the records that were public at time t. `world`
imports nothing from `agent`; a test enforces that, and that `agent` imports nothing here except `world.view`."""
