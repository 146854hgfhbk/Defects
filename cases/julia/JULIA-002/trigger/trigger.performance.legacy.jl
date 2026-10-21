println("JULIA-TRIGGER-START")
using Test
using LinearAlgebra
using LinearSolve
using Random
using Statistics

Random.seed!(1159)
BLAS.set_num_threads(1)
n = 128
parent = rand(n, n) + n * I
rhs = rand(n)

function factor_for(matrix, rhs)
    cache = init(LinearProblem(matrix, copy(rhs)), GenericLUFactorization())
    solve!(cache)
    return first(cache.cacheval)
end

function kernel_time(factor, rhs; repetitions=400)
    work = similar(rhs)
    copyto!(work, rhs)
    LinearSolve._naive_lu_ldiv!(factor.factors, factor.ipiv, work)
    elapsed = 0
    for _ in 1:repetitions
        copyto!(work, rhs)
        started = time_ns()
        LinearSolve._naive_lu_ldiv!(factor.factors, factor.ipiv, work)
        elapsed += time_ns() - started
    end
    elapsed / repetitions
end

normal_factor = factor_for(copy(parent), rhs)
adjoint_factor = factor_for(adjoint(copy(parent)), rhs)
ratios = Float64[]
for round in 1:9
    if isodd(round)
        adjoint_ns = kernel_time(adjoint_factor, rhs)
        normal_ns = kernel_time(normal_factor, rhs)
    else
        normal_ns = kernel_time(normal_factor, rhs)
        adjoint_ns = kernel_time(adjoint_factor, rhs)
    end
    push!(ratios, adjoint_ns / normal_ns)
end

@testset "JULIA-002 Adjoint GenericLU relative performance" begin
    @test median(ratios) <= 1.9
end
println("JULIA-002 trigger completed")
