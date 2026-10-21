using Test
using GenericLinearAlgebra
using LinearAlgebra

println("JULIA-TRIGGER-START")
@testset "Issue 121" begin
    @test svdvals(BigFloat[0 0; 1 -1]) ≈ [sqrt(2), 0]
    @test svdvals(BigFloat[1 0 0; 0 0 0; 0 1 -1]) ≈ [sqrt(2), 1, 0]
end
