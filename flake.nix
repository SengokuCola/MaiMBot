{
  description = "MaiMBot Nix Dev Env";
  # 本配置仅方便用于开发，但是因为 nb-cli 上游打包中并未包含 nonebot2，因此目前本配置并不能用于运行和调试

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };

        pythonEnv = pkgs.python3.withPackages (
          ps: with ps; [
            ruff
            pymongo
            python-dotenv
            pydantic
            jieba
            openai
            aiohttp
            requests
            urllib3
            numpy
            pandas
            matplotlib
            networkx
            python-dateutil
            APScheduler
            loguru
            tomli
            customtkinter
            colorama
            pypinyin
            pillow
            setuptools
          ]
        );
      in
      {
        devShell = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.nb-cli
          ];

          shellHook = ''
          '';
        };
      }
    );
}
