#!/usr/bin/env python3
import ast
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
CHECKER = REPOSITORY / "scripts" / "check_publish_workflow.py"


class CheckPublishWorkflowTests(unittest.TestCase):
    def test_checker_has_no_shadowed_functions(self) -> None:
        functions = [node.name for node in ast.parse(CHECKER.read_text()).body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertEqual(len(functions), len(set(functions)))

    def run_checker(self, workspace: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, CHECKER],
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
        )

    def copy_workspace(self, workspace: Path) -> None:
        shutil.copytree(REPOSITORY / ".github", workspace / ".github")

    def mutate(self, relative_path: str, old: str, new: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace = Path(tempdir)
            self.copy_workspace(workspace)
            path = workspace / relative_path
            original = path.read_text()
            self.assertIn(old, original)
            path.write_text(original.replace(old, new, 1))
            return self.run_checker(workspace)

    def test_current_configuration_passes(self) -> None:
        result = self.run_checker(REPOSITORY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_unterminated_composite_action_shell(self) -> None:
        result = self.mutate(
            ".github/actions/generate-bst-ci-config/action.yml",
            "        set -euo pipefail\n",
            "        if true; then\n",
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_remote_execution_configuration(self) -> None:
        result = self.mutate(
            ".github/actions/generate-bst-ci-config/action.yml",
            "          max-jobs: 2\n",
            "          max-jobs: 2\n        remote-execution:\n          execution-service:\n            url: https://cache.projectbluefin.io:11002\n",
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_build_without_local_export(self) -> None:
        result = self.mutate(
            ".github/workflows/build.yml",
            "        run: just export nvidia\n",
            "        run: just export default\n",
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_explicit_artifact_pull(self) -> None:
        result = self.mutate(
            ".github/workflows/build.yml",
            "      - name: Build OCI image with BuildStream\n",
            "      - name: Pull prebuilt artifacts from remote CAS\n"
            "        run: true\n\n"
            "      - name: Build OCI image with BuildStream\n",
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_publish_without_staging_pull(self) -> None:
        result = self.mutate(
            ".github/workflows/publish.yml",
            '          sudo podman pull "${IMAGE}:build-${BUILD_SHA}"\n',
            '          sudo podman pull "${IMAGE}:${BUILD_SHA}"\n',
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_inline_variant_matrix_drift(self) -> None:
        result = self.mutate(
            ".github/workflows/publish.yml",
            "          - variant: nvidia-gaming\n            image_suffix: '-nvidia-gaming'\n            continue: false\n",
            "",
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("drifted", result.stderr)

    def test_rejects_declaration_drift_from_workflow(self) -> None:
        result = self.mutate(
            ".github/image-variants.json",
            '"image_suffix": "-nvidia-gaming"',
            '"image_suffix": "-nvidia-game"',
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("drifted", result.stderr)

    def test_rejects_variant_missing_a_role_membership(self) -> None:
        result = self.mutate(
            ".github/image-variants.json",
            '        "scan": {},\n        "rollback": {}',
            '        "scan": {}',
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("does not declare membership", result.stderr)

    def test_rejects_duplicate_variant_image(self) -> None:
        result = self.mutate(
            ".github/image-variants.json",
            '"image": "dakota-gaming"',
            '"image": "dakota-nvidia"',
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_exclusion_without_a_reason(self) -> None:
        result = self.mutate(
            ".github/image-variants.json",
            '"excluded": "this branch locally builds only nvidia-gaming"',
            '"excluded": ""',
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_malformed_declaration(self) -> None:
        result = self.mutate(
            ".github/image-variants.json", '"variants": [', '"variants": [ ,'
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not valid JSON", result.stderr)

    def test_rejects_nvidia_gaming_sbom_becoming_gating(self) -> None:
        result = self.mutate(
            ".github/image-variants.json",
            '"sbom": {\n          "continue": true\n        }',
            '"sbom": {\n          "continue": false\n        }',
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


class ImageVariantsMatrixTests(unittest.TestCase):
    """The derived matrices must equal what publish.yml used to state inline."""

    def setUp(self) -> None:
        sys.path.insert(0, str(REPOSITORY / ".github/scripts"))
        import image_variants

        self.image_variants = image_variants
        self.declaration = image_variants.load(REPOSITORY / ".github/image-variants.json")

    def test_declaration_is_valid(self) -> None:
        self.assertEqual(self.image_variants.validate(self.declaration), [])

    def test_publish_matrix_contains_only_the_locally_built_variant(self) -> None:
        matrix = self.image_variants.matrix_for(self.declaration, "publish")
        self.assertEqual([entry["variant"] for entry in matrix], ["nvidia-gaming"])
        self.assertIs(matrix[0]["continue"], False)

    def test_sbom_matrix_contains_the_locally_built_variant(self) -> None:
        matrix = self.image_variants.matrix_for(self.declaration, "sbom")
        self.assertEqual([entry["variant"] for entry in matrix], ["nvidia-gaming"])
        self.assertEqual(matrix[0]["sbom_filename"], "dakota-nvidia-gaming.spdx.json")

    def test_role_projection_omits_undeclared_fields(self) -> None:
        matrix = self.image_variants.matrix_for(self.declaration, "tag_testing")
        for entry in matrix:
            self.assertEqual(set(entry), {"variant", "image_suffix", "continue"})

    def test_parser_preserves_scalar_types(self) -> None:
        workflow = (REPOSITORY / ".github/workflows/publish.yml").read_text()
        matrix = {
            entry["variant"]: entry
            for entry in self.image_variants.parse_workflow_matrix(
                workflow, "publish-image"
            )
        }
        # Quoting is significant: `gaming: 'true'` is a string, while
        # `continue: false` is a boolean in the local NVIDIA gaming matrix.
        self.assertEqual(matrix["nvidia-gaming"]["gaming"], "true")
        self.assertIs(matrix["nvidia-gaming"]["continue"], False)
        self.assertEqual(matrix["nvidia-gaming"]["image_suffix"], "-nvidia-gaming")

    def test_every_workflow_matrix_matches_the_declaration(self) -> None:
        workflow = (REPOSITORY / ".github/workflows/publish.yml").read_text()
        self.assertEqual(
            self.image_variants.check_workflow_drift(
                self.declaration, workflow, self.image_variants.CONSUMERS
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
