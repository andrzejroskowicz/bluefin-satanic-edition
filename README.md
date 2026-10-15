# Bluefin Satanic Edition

*A personal reboot of Ubuntu Satanic Edition, reborn on Bluefin Dakota.*

Bluefin Satanic Edition is a dark, red-accented GNOME desktop with fiery artwork and metal in the Music folder. It is built on Project Bluefin’s Dakota image, which uses GNOME OS and bootc, and is assembled from source with BuildStream.

This project takes inspiration from the old [Ubuntu Satanic Edition](https://ubuntusatanic.org/about/), an Ubuntu-based community remix that paired free software with dark artwork and metal music. This is an independent, modern reboot of that idea; it is not an Ubuntu-based image or an official continuation of the original project.

## The look

The current wallpaper features a blazing pentagram above a gothic landscape. It is included in the image and is the only wallpaper offered by the custom wallpaper chooser.

![Bluefin Satanic Edition wallpaper: a fiery pentagram above a gothic landscape](files/satanic-wallpapers/satanic-name.png)

The desktop defaults to dark mode with a red GNOME accent. Tiling Shell is opt-in, Caffeine runs without notifications, and Blur my Shell uses dynamic panel blur.

## Music

The image includes two tracks, copied into each user’s Music folder at first login:

- **Infernal Descent**
- **Lord Beneath the Flame**

[Gapless](https://flathub.org/en/apps/com.github.neithern.g4music), a GTK music player, is included as a default Flatpak preinstall. Flatpak preinstalls are processed during first boot, so the app is installed when the machine is online.

## Build the NVIDIA gaming image

This is the personal target for this project. On a Linux host with `just` and `podman`, from the repository root run:

```bash
BUILD_GAMING=true just build nvidia
```

The command builds and exports `dakota-nvidia-gaming:latest` to the local Podman image store. BuildStream runs inside the project’s configured container. For build and contribution details, see [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## AI and project disclaimer

**AI-use notice:** Some or all of the artwork, music, and supporting project materials were created with generative AI, with human direction and editing. They may contain errors or artifacts, and their provenance may not always be independently verifiable.

This is an independent personal project. It is not affiliated with Canonical, Ubuntu, the original Ubuntu Satanic Edition project, or Project Bluefin. Product names and trademarks belong to their respective owners.
