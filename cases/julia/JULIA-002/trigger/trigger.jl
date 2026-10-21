println("JULIA-TRIGGER-START")
using Test
using LinearAlgebra
using LinearSolve

@testset "JULIA-002 Adjoint/Transpose specialized kernel dispatch" begin
    ipivT = Vector{LinearAlgebra.BlasInt}
    for W in (Adjoint, Transpose), rhsT in (Vector{Float64}, Matrix{Float64})
        @test which(
            LinearSolve._naive_lu_ldiv!,
            Tuple{W{Float64, Matrix{Float64}}, ipivT, rhsT}
        ) !== which(
            LinearSolve._naive_lu_ldiv!,
            Tuple{Matrix{Float64}, ipivT, rhsT}
        )
    end
end
println("JULIA-002 trigger completed")
