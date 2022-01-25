import os
import pathlib
import subprocess

from sphinx.ext.doctest import (Any, Dict, DocTestBuilder, TestcodeDirective,
                                TestoutputDirective, doctest, sphinx)
from sphinx.locale import __


class JavaDocTestBuilder(DocTestBuilder):
    """
    Runs java test snippets in the documentation.
    """

    name = "javadoctest"
    epilog = __(
        "Java testing of doctests in the sources finished, look at the "
        "results in %(outdir)s/output.txt."
    )

    def compile(
        self, code: str, name: str, type: str, flags: Any, dont_inherit: bool
    ) -> Any:
        # go to project that contains all your arrow maven dependencies
        path_arrow_project = pathlib.Path(__file__).parent.parent / "source" / "demo"

        # create list of all arrow jar dependencies
        subprocess.check_call(
            [
                "mvn",
                "-q",
                "dependency:build-classpath",
                "-DincludeTypes=jar",
                "-Dmdep.outputFile=.cp.tmp",
            ],
            cwd=path_arrow_project,
            text=True,
        )
        if not (path_arrow_project / ".cp.tmp").exists():
            raise RuntimeError(
                __("invalid process to create jshell dependencies library")
            )

        # get list of all arrow jar dependencies
        with open(path_arrow_project / ".cp.tmp") as f:
            stdout_dependency = f.read()
        if not stdout_dependency:
            raise RuntimeError(
                __("invalid process to list jshell dependencies library")
            )

        # execute java testing code thru jshell and read output
        # JDK11 support '-' This allows the pipe to work as expected without requiring a shell
        # Migrating to /dev/stdin to also support JDK9+
        proc_jshell_process = subprocess.Popen(
            ["jshell", "--class-path", stdout_dependency, "-s", "/dev/stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        out_java_arrow, err_java_arrow = proc_jshell_process.communicate(code)
        if err_java_arrow:
            raise RuntimeError(__("invalid process to run jshell"))

        # continue with python logic code to do java output validation
        output = f"print('''{self.clean_output(out_java_arrow)}''')"

        # continue with sphinx default logic
        return compile(output, name, self.type, flags, dont_inherit)

    def clean_output(self, output: str):
        if output[-3:] == '-> ':
            output = output[:-3]
        if output[-1:] == '\n':
            output = output[:-1]
        output = (4*' ').join(output.split('\t'))
        return output

def setup(app) -> Dict[str, Any]:
    app.add_directive("testcode", TestcodeDirective)
    app.add_directive("testoutput", TestoutputDirective)
    app.add_builder(JavaDocTestBuilder)
    # this config value adds to sys.path
    app.add_config_value("doctest_path", [], False)
    app.add_config_value("doctest_test_doctest_blocks", "default", False)
    app.add_config_value("doctest_global_setup", "", False)
    app.add_config_value("doctest_global_cleanup", "", False)
    app.add_config_value(
        "doctest_default_flags",
        doctest.DONT_ACCEPT_TRUE_FOR_1
        | doctest.ELLIPSIS
        | doctest.IGNORE_EXCEPTION_DETAIL,
        False,
    )
    return {"version": sphinx.__display_version__, "parallel_read_safe": True}