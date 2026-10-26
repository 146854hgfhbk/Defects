package.path = "./lua/?.lua;./lua/?/init.lua;"..package.path
local strict = require "pl.strict"
local M = strict.module({}, {})
local ok, err = pcall(function() return M.undeclared_global end)
assert(not ok, "access to undeclared global must error")
assert(tostring(err):find("is not declared"), "error must survive non-string module name, got: "..tostring(err):sub(1,90))
local ok2 = pcall(function() _G._PROMPT2 = "probe" end)
assert(ok2, "_PROMPT2 must be predeclared under global strict")
print("PASS")
