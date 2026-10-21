using Test
using DataStructures

println("JULIA-TRIGGER-START")
@testset "Fixes issue 857" begin
    h = OrderedRobinDict{Any,Any}([("a", missing), ("b", -2)])
    @test 5 == (h["a"] = 5)
    @test "b" in keys(h)
    @test haskey(h, "b")
end
