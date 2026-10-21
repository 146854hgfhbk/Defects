using Test
using StatsBase

println("JULIA-TRIGGER-START")
@testset "inverse_rle validates run lengths" begin
    @test_throws DimensionMismatch inverse_rle([1, 2], [1])
end
