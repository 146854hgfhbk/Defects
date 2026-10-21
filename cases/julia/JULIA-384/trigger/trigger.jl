using Test
using Krylov
using LinearAlgebra

function breakdown_matrix(transpose_matrix=false)
    matrix = transpose_matrix ? [1.0 -1.0; 0.0 1.0; -1.0 0.0] :
                                  [1.0 0.0 -1.0; -1.0 1.0 0.0]
    rows, columns = size(matrix)
    return matrix, ones(rows), ones(columns)
end

println("JULIA-TRIGGER-START")
@testset "GPMR inconsistent systems" begin
    for transpose_matrix in (false, true)
        matrix, b, c = breakdown_matrix(transpose_matrix)
        system = [I matrix; matrix' I]
        rhs = [b; c]
        @test rank(system) < size(system, 1)
        x, y, stats = gpmr(matrix, matrix', b, c)
        residual = rhs - system * [x; y]
        normal_residual = norm(system' * residual) / norm(system' * rhs)
        @test normal_residual <= 1.0e-6
        @test stats.inconsistent
    end
end
