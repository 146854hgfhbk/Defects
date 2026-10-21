module Julia205Issue218

using Test
using Comonicon

println("JULIA-TRIGGER-START")

@cast function print(file)
    if splitext(file)[2] == ".toml"
        print("safe local output")
    else
        error("user-defined print was called while rendering help")
    end
end

@main

@testset "JULIA-205 static help uses Base.print" begin
    @test Julia205Issue218.command_main(["-h"]) == 0
end

end
