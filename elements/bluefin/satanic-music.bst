kind: manual

sources:
- kind: local
  path: files/dakota-music

build-depends:
- core/sandbox-tools.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - |
    install -Dm644 "Infernal Descent.mp3" \
      "%{install-root}%{datadir}/dakota/music/Infernal Descent.mp3"
    install -Dm644 "Lord Beneath the Flame.mp3" \
      "%{install-root}%{datadir}/dakota/music/Lord Beneath the Flame.mp3"
    install -Dm755 dakota-seed-music \
      "%{install-root}%{libexecdir}/dakota-seed-music"
    install -Dm644 dakota-seed-music.service \
      "%{install-root}%{libdir}/systemd/user/dakota-seed-music.service"
    install -d "%{install-root}%{libdir}/systemd/user/default.target.wants"
    ln -s ../dakota-seed-music.service \
      "%{install-root}%{libdir}/systemd/user/default.target.wants/dakota-seed-music.service"
  - "%{install-extra}"
