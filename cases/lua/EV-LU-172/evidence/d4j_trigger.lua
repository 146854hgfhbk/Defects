package.path = "./lua/?.lua;./lua/?/init.lua;"..package.path
local Date = require "pl.Date"
local today = Date()
local f = Date.Format("yyyy")
local d = f:parse(tostring(today:year()))
assert(d, "parse returned nil")
assert(d:day() == today:day(),
  string.format("parse must default day to today's day (%d), got %d", today:day(), d:day()))
print("PASS")
