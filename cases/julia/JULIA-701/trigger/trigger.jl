using Test
using Configurations

println("JULIA-TRIGGER-START")
@option struct MacroExpand
    x = 1
    @static if true
        y = 2
    end
end

@testset "macroexpand (#39)" begin
    @test fieldnames(MacroExpand) == (:x, :y)
end
