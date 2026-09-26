# [1.2.0](https://github.com/SOKTeam/S.O.K/compare/v1.1.0...v1.2.0) (2026-09-26)


### Bug Fixes

* **file-ops:** replace existing destination files when organizing ([341cd81](https://github.com/SOKTeam/S.O.K/commit/341cd815b595bb15619cb269c9a6fdd47e436fe5))
* **file-ops:** support moves across different drives ([23f7a04](https://github.com/SOKTeam/S.O.K/commit/23f7a0460cf8d6912f4411f031dffba7a2e84892))
* **i18n:** add missing translation keys ([ad67825](https://github.com/SOKTeam/S.O.K/commit/ad678254d8ddb4ec3f2cb4f3f9c84d54794a94a6))
* **macos:** give the sidebar more room ([33815f9](https://github.com/SOKTeam/S.O.K/commit/33815f9dc04689c6b6eeae0af4db71379f50f9b9))
* **macos:** keep settings and logs outside the app bundle ([9aeaae3](https://github.com/SOKTeam/S.O.K/commit/9aeaae395fb0e9d72c240ab5e242f2b684e21d70))
* **macos:** keep the window title centered in built apps ([fb4fb94](https://github.com/SOKTeam/S.O.K/commit/fb4fb94d24ccdc9b9cdfed51fbe51297b23106b9))
* **macos:** match the native chrome to a forced theme ([f1fe41d](https://github.com/SOKTeam/S.O.K/commit/f1fe41d4adaa7fad4c4947473738c1be0662ecc6))
* **macos:** show the page name in the native window title ([e4a2dc6](https://github.com/SOKTeam/S.O.K/commit/e4a2dc6d5b5a22bbbdb2cae5fc8a23d048d4ad80))
* **movies:** scan folders dropped on the movies page ([b332af2](https://github.com/SOKTeam/S.O.K/commit/b332af2378c59c28833e665c80a8c2648bac5ead))
* **organize:** support organizing music, books and games ([54c9b37](https://github.com/SOKTeam/S.O.K/commit/54c9b378c2c2912f035b0f3d8988e818a9f959f1))
* **tools:** make verify_i18n detect tr() calls ([c0c9bf9](https://github.com/SOKTeam/S.O.K/commit/c0c9bf99e45303e9704e33c92a56c02b6b01a97a))
* **ui:** show a single dialog when a background task fails ([7ee4357](https://github.com/SOKTeam/S.O.K/commit/7ee4357812bd96653ff3c5ec2a0a9aa7acb14a3c))
* **ui:** stop a blank window flashing at startup on Windows ([eba919a](https://github.com/SOKTeam/S.O.K/commit/eba919ad8ef7a2f65d644dac70049e2a06721ccf))
* **ui:** use default folders from settings as destination ([9807b77](https://github.com/SOKTeam/S.O.K/commit/9807b77401a07eced9b087ce109e10c185672877))
* **ui:** use the real macOS system font family name ([9fdc4c5](https://github.com/SOKTeam/S.O.K/commit/9fdc4c57aefaf4ac113f2b38da9345cfbe397395))
* **video:** match video extensions case-insensitively ([bda772f](https://github.com/SOKTeam/S.O.K/commit/bda772f37b4bcf4c3d9d435c314b9e8439b4e3b2))
* **video:** move files in organize_files without a progress callback ([28798c7](https://github.com/SOKTeam/S.O.K/commit/28798c781df3170f83f8530d271cac189e4de5b3))


### Features

* **macos:** add a native menu bar with standard shortcuts ([4bdbf35](https://github.com/SOKTeam/S.O.K/commit/4bdbf356d4e213c6154b1f900ff79679ff042b9a))
* **macos:** add a white and gray light palette ([1022b7c](https://github.com/SOKTeam/S.O.K/commit/1022b7c7f253a36c43053fcc8f91fb043608674c))
* **macos:** add an option to use the system accent color ([6018167](https://github.com/SOKTeam/S.O.K/commit/6018167477415565db4458d6c71c792280df1f5d))
* **macos:** bounce the Dock icon when a task ends in the background ([e02d360](https://github.com/SOKTeam/S.O.K/commit/e02d36042f07fedb3140ae97e6f5b44b3a56286a))
* **macos:** download the disk image when updating ([4e96d43](https://github.com/SOKTeam/S.O.K/commit/4e96d43c67b5672fc0a5d9c7245cf28ac74f46bd))
* **macos:** draw a proper macOS app icon ([cb54744](https://github.com/SOKTeam/S.O.K/commit/cb54744ec5f8e7e7c04f1f2812504e89df18e6bf))
* **macos:** follow the system light/dark appearance ([38d8005](https://github.com/SOKTeam/S.O.K/commit/38d800506ac74373f028dba08ef37f5b087a1348))
* **macos:** give the sidebar a Finder look ([20f5247](https://github.com/SOKTeam/S.O.K/commit/20f5247ad005d1d70cf239b6715a33e2beb22c1c))
* **macos:** keep the native scroll bars ([6d44f64](https://github.com/SOKTeam/S.O.K/commit/6d44f648a9b8421ea35a914758dd2ad5b1a9c72f))
* **macos:** list the startup disk and mounted volumes ([0cdc1f5](https://github.com/SOKTeam/S.O.K/commit/0cdc1f55684acdf897b7a047c83bd1fcfeef04bc))
* **macos:** offer to show the destination in the Finder ([3e457af](https://github.com/SOKTeam/S.O.K/commit/3e457af987dbd408e530671bd2bdbffaf3834048))
* **macos:** show message boxes as window sheets ([1b1061b](https://github.com/SOKTeam/S.O.K/commit/1b1061b474b995be165ea0afbf0535244aacb6d3))
* **macos:** use Mac sizes and sentence-case headings ([6f03935](https://github.com/SOKTeam/S.O.K/commit/6f039352ce36fe76f16e72416dbb601c977ff0aa))
* **macos:** use the native window with traffic lights ([4bc04b0](https://github.com/SOKTeam/S.O.K/commit/4bc04b03518a514a523de059b0f1f0f558d353f6))

# [1.1.0](https://github.com/SOKTeam/S.O.K/compare/v1.0.1...v1.1.0) (2026-06-02)


### Features

* **ui:** add dedicated movies page with batch rename ([1f0be8e](https://github.com/SOKTeam/S.O.K/commit/1f0be8e7ae40645d68a12f18809c2a0c24e6b72b))

## [1.0.1](https://github.com/SOKTeam/S.O.K/compare/v1.0.0...v1.0.1) (2026-05-05)


### Bug Fixes

* **ui:** resolve organize hang, fullscreen ghost bar and broaden series regex ([#1](https://github.com/SOKTeam/S.O.K/issues/1)) ([eb261f3](https://github.com/SOKTeam/S.O.K/commit/eb261f39e23e34c488794206ac417d31ef2f4a03))

# 1.0.0 (2026-01-04)


### Features

* **core:** initial S.O.K v1.0.0 release ([11cb1ee](https://github.com/SOKTeam/S.O.K/commit/11cb1ee7a4be476aa57be4a308bec3d36a53ec73))

# 1.0.0 (2026-01-04)


### Features

* **core:** initial S.O.K v1.0.0 release ([3967b42](https://github.com/SOKTeam/S.O.K/commit/3967b42699bc86dabef12d97c8a6bd4e238e5d39))
