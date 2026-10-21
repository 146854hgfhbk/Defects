using Pkg, JET
println("JULIA-TRIGGER-START")
old_project = Base.active_project()
try
    mktempdir() do tmp
        pkgpath = joinpath(tmp, "MultiModuleInclude")
        Pkg.generate(pkgpath; io=devnull)
        write(joinpath(pkgpath, "src", "MultiModuleInclude.jl"),
              "module MultiModuleInclude\nmodule A\ninclude(\"shared.jl\")\nend\nmodule B\ninclude(\"shared.jl\")\nend\nend\n")
        write(joinpath(pkgpath, "src", "shared.jl"), "shared() = shared_missing\n")
        Pkg.activate(; temp=true, io=devnull)
        Pkg.develop(; path=pkgpath, io=devnull)
        Pkg.precompile(; io=devnull)
        pkgid, _ = JET.find_pkg("MultiModuleInclude")
        pkgmod = Base.require(pkgid)
        result = JET.report_package(pkgmod; toplevel_logger=nothing)
        reports = JET.get_reports(result)
        matches = count(r -> occursin("shared_missing", sprint(show, r)), reports)
        matches == 2 || error("expected two reports for a file included by two modules, got $matches")
    end
finally
    old_project === nothing || Pkg.activate(dirname(old_project); io=devnull)
end
println("JULIA-581 trigger completed")
