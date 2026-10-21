using Test
using StaticArrays

println("JULIA-TRIGGER-START")

@testset "JULIA-509 Any StaticArray view dimensions" begin
    vector = SVector{4,Any}(1, 2, 3, 4)
    @test (@inferred view(vector, SA[3, 1])) == SVector{2,Any}(3, 1)

    matrix = SMatrix{2,2,Any}(1, 2, 3, 4)
    @test (@inferred view(matrix, @SArray(fill(1, 1, 1)))) == SMatrix{1,1,Any}(1)

    cube = SArray{Tuple{2,2,2},Any}(1, 2, 3, 4, 5, 6, 7, 8)
    @test (@inferred view(cube, @SArray(fill(1, 1, 1, 1)))) == SArray{Tuple{1,1,1},Any}(1)
end
