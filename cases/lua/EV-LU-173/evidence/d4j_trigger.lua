local _ = require "moses"
local t = {}
for i = 1, 64 do t["k"..i] = i end
local expected = {}
for k, v in pairs(t) do expected[#expected+1] = v end
local r = _.select(t, function() return true end)
assert(#r == #expected, "select must keep all values")
for i = 1, #r do
  assert(r[i] == expected[i], "select must preserve pairs(t) order, differs at index "..i)
end
print("PASS")
