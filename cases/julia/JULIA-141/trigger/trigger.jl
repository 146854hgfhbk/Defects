using Test
using SciMLBase

println("JULIA-TRIGGER-START")
@testset "SciMLBase precompiles without deprecation warnings" begin
    script = """Base.compilecache(Base.identify_package("SciMLBase"))"""
    cmd = `$(Base.julia_cmd()) --startup-file=no --project=$(Base.active_project()) -e $script`
    buf = IOBuffer()
    run(pipeline(ignorestatus(cmd), stdout=buf, stderr=buf))
    output = String(take!(buf))
    @test !occursin("deprecated", output)
end
