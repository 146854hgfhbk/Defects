local inspect = require "inspect"
local out = inspect({{1}})
assert(out == "{ { 1 } }", "non-repeated tables must not get ids, got: "..out)
print("PASS")
