package.path = "./lua/?.lua;./lua/?/init.lua;"..package.path
local Map = require "pl.Map"
local m = Map(); m.alpha = 1; m.beta = 2
local ks = m:keys()
local ok, err = pcall(function() return ks:sort() end)
assert(ok, "Map:keys() must return a usable pl.List: "..tostring(err))
assert(ks[1] == "alpha" and ks[2] == "beta", "sorted keys wrong: "..tostring(ks[1])..","..tostring(ks[2]))
local its = m:items()
assert(its[1][1] == "alpha" and its[2][1] == "beta", "items() must return sorted List pairs")
print("PASS")
