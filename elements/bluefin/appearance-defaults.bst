kind: manual

sources:
- kind: local
  path: files/dconf

build-depends:
- core/sandbox-tools.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - |
    install -Dm644 09-dakota-appearance-defaults \
      "%{install-root}%{sysconfdir}/dconf/db/distro.d/09-dakota-appearance-defaults"
  - "%{install-extra}"
