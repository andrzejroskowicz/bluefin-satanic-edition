#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path('.')
PUBLISH = ROOT / '.github/workflows/publish.yml'
BUILD = ROOT / '.github/workflows/build.yml'
CI_CONFIG_ACTION = ROOT / '.github/actions/generate-bst-ci-config/action.yml'
VARIANTS = ROOT / '.github/image-variants.json'
sys.path.insert(0, str((ROOT / '.github/scripts').resolve()))
import image_variants  # noqa: E402


def extract_composite_shell(action: str) -> str | None:
    run_indent = None
    shell_lines = []
    for line in action.splitlines(keepends=True):
        if run_indent is None:
            match = re.match(r'^(?P<indent> *)run: \|\s*$', line)
            if match:
                run_indent = len(match.group('indent'))
            continue
        if line.strip() and len(line) - len(line.lstrip()) <= run_indent:
            break
        shell_lines.append(line)
    if run_indent is None:
        return None
    return textwrap.dedent(''.join(shell_lines))


def check_local_config(shell: str, action: str, errors: list[str]) -> None:
    syntax = subprocess.run(['bash', '-n'], input=shell, text=True, capture_output=True, check=False)
    if syntax.returncode:
        errors.append(f'local BuildStream config shell is invalid: {syntax.stderr.strip()}')
        return
    with tempfile.TemporaryDirectory() as tempdir:
        workspace = Path(tempdir)
        result = subprocess.run(
            ['bash', '-c', shell], cwd=workspace,
            env={**os.environ, 'GITHUB_WORKSPACE': str(workspace)},
            text=True, capture_output=True, check=False,
        )
        config_path = workspace / 'buildstream-ci.conf'
        config = config_path.read_text() if config_path.exists() else ''
        if result.returncode:
            errors.append('local BuildStream config generation failed: ' + (result.stderr.strip() or result.stdout.strip()))
        for token in ('max-jobs: 2', 'cache-buildtrees: never', 'fetchers: 16'):
            if token not in config:
                errors.append(f'local BuildStream config is missing {token!r}')
        for token in ('remote-execution:', 'storage-service:', 'artifacts:', 'source-caches:', 'cache.projectbluefin.io'):
            if token in config or token in action:
                errors.append(f'local BuildStream configuration still contains remote CAS setting {token!r}')
    for token in ('CASD_CLIENT_CERT', 'CASD_CLIENT_KEY', 'enable-remote-execution', 'enable-push'):
        if token in action:
            errors.append(f'local config action still references {token}')


def check_build_workflow(build: str, errors: list[str]) -> None:
    required = {
        'uses: ./.github/actions/generate-bst-ci-config': 'local BuildStream configuration',
        'just export nvidia': 'local OCI export from the nvidia element',
        'build-${BUILD_SHA}': 'GHCR staging image for publish.yml',
        'packages: write': 'GHCR write permission for the staging image',
    }
    for token, description in required.items():
        if token not in build:
            errors.append(f'build workflow is missing {description}')
    for token in ('CASD_CLIENT_CERT', 'CASD_CLIENT_KEY', 'enable-remote-execution', 'cache.projectbluefin.io', 'Remote Execution Configuration'):
        if token in build:
            errors.append(f'build workflow still references remote CAS/execution setting {token}')
    if 'Push PR image' not in build or 'Push staging image for publish workflow' not in build:
        errors.append('build workflow must push PR and staging images from the local build job')
    if 'Pull prebuilt artifacts from remote CAS' in build:
        errors.append('build workflow must not depend on an explicit remote CAS pre-pull')


def check_image_variants(publish: str, errors: list[str]) -> None:
    try:
        declaration = image_variants.load(VARIANTS)
    except image_variants.DeclarationError as exc:
        errors.append(str(exc))
        return
    errors.extend(image_variants.validate(declaration))
    if errors:
        return
    errors.extend(image_variants.check_workflow_drift(declaration, publish, image_variants.CONSUMERS))
    sbom = {entry['variant']: entry for entry in image_variants.matrix_for(declaration, 'sbom')}
    gaming = sbom.get('nvidia-gaming')
    if gaming is None:
        errors.append('publish-sbom must include the locally built nvidia-gaming image')
    else:
        if gaming.get('continue') is not True:
            errors.append('publish-sbom nvidia-gaming must remain non-gating')
        if gaming.get('sbom_filename') != 'dakota-nvidia-gaming.spdx.json':
            errors.append('publish-sbom must emit dakota-nvidia-gaming.spdx.json')


def check_publish_workflow(publish: str, errors: list[str]) -> None:
    required = {
        'branches:\n      - satanic-branding': 'Satanic Edition branch trigger',
        'sudo podman pull "${IMAGE}:build-${BUILD_SHA}"': 'staged image pull by the resolved build SHA',
        'sign-and-publish@v1': 'keyless image signing and attestation',
        'dakota-nvidia-gaming.spdx.json': 'gaming SBOM attachment',
        'testing_tag=satanic-branding': 'Satanic Edition rolling tag',
    }
    for token, description in required.items():
        if token not in publish:
            errors.append(f'publish workflow is missing {description}')
    for token in ('CASD_CLIENT_CERT', 'CASD_CLIENT_KEY', 'enable-remote-execution', 'cache.projectbluefin.io', 'remote-execution:'):
        if token in publish:
            errors.append(f'publish workflow still references remote CAS/execution setting {token}')
    if 'generate-sbom: false' not in publish:
        errors.append('publish workflow must preserve its explicit BST-native SBOM handling')


def main() -> int:
    errors: list[str] = []
    publish = PUBLISH.read_text()
    build = BUILD.read_text()
    action = CI_CONFIG_ACTION.read_text()
    shell = extract_composite_shell(action)
    if shell is None:
        errors.append('could not find composite action shell in local BuildStream config action')
    else:
        check_local_config(shell, action, errors)
    check_build_workflow(build, errors)
    check_publish_workflow(publish, errors)
    check_image_variants(publish, errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print('local build, publish, and BuildStream CI configuration checks passed')
    return 0

if __name__ == '__main__':
    sys.exit(main())
