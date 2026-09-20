class Frostylauncher < Formula
  include Language::Python::Virtualenv

  desc "Install and launch Blizzard games on Linux via umu-launcher + Proton"
  homepage "https://github.com/OWNER/frostylauncher"
  url "https://github.com/OWNER/frostylauncher/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_TARBALL_SHA256"
  license "MIT"
  head "https://github.com/OWNER/frostylauncher.git", branch: "main"

  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      frostylauncher drives the host's umu-launcher + a Proton build.
      Make sure umu-run is available and a GE-Proton/UMU-Proton build exists in a
      compatibilitytools.d directory (e.g. via ProtonPlus).

      Check with:  frostylauncher doctor
      GUI:         frostylauncher gui
    EOS
  end

  test do
    system "#{bin}/frostylauncher", "--version"
  end
end
