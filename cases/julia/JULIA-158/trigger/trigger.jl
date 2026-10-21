using Test
using LinearSolve
using GPUArraysCore
using LinearAlgebra
using SciMLOperators: WOperator

struct MinimalGPUVector{T} <: GPUArraysCore.AbstractGPUArray{T,1}
    data::Vector{T}
end
Base.size(vector::MinimalGPUVector) = size(vector.data)
Base.getindex(vector::MinimalGPUVector, index::Int) = vector.data[index]
Base.IndexStyle(::Type{<:MinimalGPUVector}) = IndexLinear()

println("JULIA-TRIGGER-START")
@testset "WOperator with a GPU right-hand side" begin
    operator = WOperator{true}(I, 0.1, Matrix{Float64}(I, 2, 2), zeros(2))
    algorithm = LinearSolve.defaultalg(
        operator,
        MinimalGPUVector(ones(2)),
        LinearSolve.OperatorAssumptions(true),
    )
    @test algorithm.alg === LinearSolve.DefaultAlgorithmChoice.KrylovJL_GMRES
end
