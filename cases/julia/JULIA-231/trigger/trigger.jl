using Test
using Ferrite
using StaticArrays

println("JULIA-TRIGGER-START")

@testset "JULIA-231 embedded line weighted normal" begin
    jacobian = @SMatrix [3.0; 4.0]
    first_normal = Ferrite.weighted_normal(jacobian, Ferrite.RefLine, 1)
    second_normal = Ferrite.weighted_normal(jacobian, Ferrite.RefLine, 2)
    @test first_normal[1] == -3.0
    @test first_normal[2] == -4.0
    @test second_normal[1] == 3.0
    @test second_normal[2] == 4.0
end
