-- busted --helper: busted itself loads the system Penlight (pl.*) before any spec runs,
-- so specs of Penlight-based projects would test the installed library instead of the
-- checkout. Drop the already-loaded copies so `require "pl.x"` resolves via the
-- checkout's package.path (cwd-relative lua/ and src/ trees).
package.path = "./lua/?.lua;./lua/?/init.lua;./src/?.lua;./src/?/init.lua;" .. package.path
for name in pairs(package.loaded) do
  if name == "pl" or name:sub(1, 3) == "pl." then package.loaded[name] = nil end
end
