using Test
using LinearAlgebra
using GenericLinearAlgebra

println("JULIA-TRIGGER-START")

@testset "JULIA-686 zero BigFloat SVD preserves singular vectors" begin
    factorization = svd(zeros(BigFloat, 2, 2))
    @test factorization.S == zeros(2)
    @test factorization.U == I
    @test factorization.Vt == I
end
