println("JULIA-TRIGGER-START")
using Test
using DiskArrays
using DiskArrays.TestTypes

@testset "JULIA-200 scalar dimensional bounds" begin
    DiskArrays.allow_scalar(true)
    array = AccessCountDiskArray(reshape(1:24, 2, 3, 4), chunksize=(2, 2, 2))
    @test array[1, 2, 3] == 15
    @test array[1, 2, 3, 1] == 15
    @test_throws BoundsError array[1, 2]
    @test array[CartesianIndex(1, 2), 3] == 15
    @test array[CartesianIndex(1, 2, 3)] == 15
end
