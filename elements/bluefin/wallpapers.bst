kind: manual

sources:
- kind: local
  path: files/satanic-wallpapers

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - |
    for image in *.png; do
      install -Dm644 "$image" "%{install-root}%{datadir}/backgrounds/bluefin/$image"
    done
    for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
      install -Dm644 satanic.xml.in "%{install-root}%{datadir}/backgrounds/bluefin/${month}-bluefin.xml"
    done
    install -Dm644 satanic-wallpapers.xml "%{install-root}%{datadir}/gnome-background-properties/satanic-wallpapers.xml"
  - "%{install-extra}"
