using Test
using LinearSolve
using LinearAlgebra
using SparseArrays
using Random

println("JULIA-TRIGGER-START")
@testset "SupernodalLU refine dispatch" begin
    SNLU = LinearSolve.SupernodalLU
    diagonal = 10.0 .^ range(-9, 9; length=200)
    matrix = spdiagm(
        0 => diagonal,
        1 => fill(1.0e-9, 199),
        -1 => fill(1.0e-9, 199),
    )
    factor = SNLU.snlu(matrix; matching=false, check=false)
    @test SNLU.nperturbed(factor) > 0
    @test SNLU._refine_steps(factor, 2) == 2
    @test SNLU._refine_steps(factor, :auto) == 3
    rhs = randn(size(matrix, 1))
    @test_throws ArgumentError SNLU.solve!(similar(rhs), factor, rhs; refine=:bogus)
end
