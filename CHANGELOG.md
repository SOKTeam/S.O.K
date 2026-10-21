# [1.4.0](https://github.com/SOKTeam/S.O.K/compare/v1.3.1...v1.4.0) (2026-10-21)


### Bug Fixes

* **apis:** give their key to the free APIs that take one ([ca93d0b](https://github.com/SOKTeam/S.O.K/commit/ca93d0b52e5887e39b2395f2161e5f98e7352614))
* **apis:** report HTTP errors instead of empty results ([63c8272](https://github.com/SOKTeam/S.O.K/commit/63c8272229c62643e3206870281689e047d02137))
* **config:** remove the settings and variables that did nothing ([471bb16](https://github.com/SOKTeam/S.O.K/commit/471bb16319ba7194d858a209dcfe3e5ef751e20e))
* **core:** give the type checker the type of the folders to remove ([75074d2](https://github.com/SOKTeam/S.O.K/commit/75074d2c15f8bfb4c3947749e322e32215cf117c))
* **file-ops:** give detected groups the same title on every system ([6983c89](https://github.com/SOKTeam/S.O.K/commit/6983c8951dbd550ea5ddd883b9a58b1a4b372694))
* **games:** remove the console name at the end of RAWG titles ([0718da2](https://github.com/SOKTeam/S.O.K/commit/0718da252434bdf36db88554c3cf413bc3171b76))
* **games:** remove the release year at the end of RAWG titles ([6589e49](https://github.com/SOKTeam/S.O.K/commit/6589e4914efd28b6044a2851aa7c8d84a1c7747b))
* **macos:** download the update disk image from the update dialog ([4a22ccb](https://github.com/SOKTeam/S.O.K/commit/4a22ccb7bc0bdf9e72e957628acde43947c41edc))
* **movies:** keep rows at the top of the table ([78c38f3](https://github.com/SOKTeam/S.O.K/commit/78c38f3a63901d2bf4f8e810d87c72360217fa62))
* **music:** skip audio files whose tags cannot be read ([bc010de](https://github.com/SOKTeam/S.O.K/commit/bc010de1dd2d4e5eab91bc29d5e36d59a8b48d9f))
* **music:** stop putting tracks on compilations found by MusicBrainz ([70a2c04](https://github.com/SOKTeam/S.O.K/commit/70a2c0430a32798c9f9c25431ee667cc873264af))
* **ui:** draw progress bars with the app accent color ([51a0403](https://github.com/SOKTeam/S.O.K/commit/51a0403386558160492617015b2281ff40d75aa0))
* **ui:** give Windows and Linux their own toggle switch ([a5efb06](https://github.com/SOKTeam/S.O.K/commit/a5efb06d08c39fc4deb6e26e37048563eaa037d3))
* **video:** take the last year of a movie name, not a number of its title ([5285f1b](https://github.com/SOKTeam/S.O.K/commit/5285f1b999cf83e7ee0ccd7322800a128927340f))


### Features

* **books:** rename books in batches, like movies ([ba8b599](https://github.com/SOKTeam/S.O.K/commit/ba8b599a3e55b643769bfa1f9a7a4a00bfc2e548))
* **core:** match files in batches with a strict Ready status ([eb165aa](https://github.com/SOKTeam/S.O.K/commit/eb165aa86ea6e4aec4bdd400ca7cbd5fb649ab1c))
* **core:** record each rename in a history that can undo it ([ca481e7](https://github.com/SOKTeam/S.O.K/commit/ca481e7fcc38a0f81e5b5ec60fe8fd3b9d43be6a))
* **file-ops:** detect the media type of dropped files ([e337467](https://github.com/SOKTeam/S.O.K/commit/e33746764b6e61667ea316db6cafe97c1db82c08))
* **file-ops:** download posters and covers next to the organized files ([a88c43d](https://github.com/SOKTeam/S.O.K/commit/a88c43dd9045f9911d47833fc84a6947c622665e))
* **games:** rename games in batches, like movies and books ([12ab3ef](https://github.com/SOKTeam/S.O.K/commit/12ab3efd59a10a8196f7bc77f5cc66d6c3ef07f2))
* **music:** name album tracks with the music format, drop the Artist search ([4d36e7b](https://github.com/SOKTeam/S.O.K/commit/4d36e7b424658ec0ca195cd7efbe5e16b17e63f6))
* **music:** rename tracks in batches in a Tracks tab ([ccf6c8a](https://github.com/SOKTeam/S.O.K/commit/ccf6c8a0aa28eabba2d30ad37417ef6b187c2257))
* **music:** search tracks in the four music APIs ([d3f9a16](https://github.com/SOKTeam/S.O.K/commit/d3f9a166d6081aa0e4837503b29b151c876ff8e2))
* **organize:** add book and game name formats to the settings ([3cec65d](https://github.com/SOKTeam/S.O.K/commit/3cec65d6a3c3466876d95d51e65d964351477a5a))
* **organize:** read file names with patterns from the settings ([910d597](https://github.com/SOKTeam/S.O.K/commit/910d59729a650953babae25ae319eb75e8ea6466))
* **ui:** add a History page and an Undo button after each rename ([054bdad](https://github.com/SOKTeam/S.O.K/commit/054bdad93f573812b050d6abbc0ff9f11763776d))
* **ui:** explain API errors to the user in their language ([6010dd1](https://github.com/SOKTeam/S.O.K/commit/6010dd14cb56893622e107316a24a6de72de9e29))
* **ui:** open the files dropped on the home page in the batch pages ([807c796](https://github.com/SOKTeam/S.O.K/commit/807c7967f0f843d56efd5963786e61c0d7dd8569))
* **ui:** sort files dropped on the home page by media type ([086360f](https://github.com/SOKTeam/S.O.K/commit/086360fea747cd085c3bd2db7493ef706cf4c345))

## [1.3.1](https://github.com/SOKTeam/S.O.K/compare/v1.3.0...v1.3.1) (2026-10-16)


### Bug Fixes

* **core:** quit the app once the update installer is launched ([49e62d3](https://github.com/SOKTeam/S.O.K/commit/49e62d360e259945a58d59b3690f93c6850f5af8))
* **ui:** cancel the previous search instead of waiting for it ([6e90cdf](https://github.com/SOKTeam/S.O.K/commit/6e90cdf5b607091dacebe64f8ee58e81025159c5))
* **ui:** show the update dialog with the theme colors ([c551bf0](https://github.com/SOKTeam/S.O.K/commit/c551bf08ae1203390b2145a9d878157ce2dba43b))

# [1.3.0](https://github.com/SOKTeam/S.O.K/compare/v1.2.0...v1.3.0) (2026-10-16)


### Bug Fixes

* **apis:** give the type checker a non-optional session ([031323c](https://github.com/SOKTeam/S.O.K/commit/031323c0ded735ceb39f401a1a9300ef47822db4))
* **apis:** open a new HTTP session for each search worker ([c8aef12](https://github.com/SOKTeam/S.O.K/commit/c8aef12e479899f45273afb5e070a5ef5086c849))
* **deps:** declare python-dotenv as a runtime dependency ([7afcd92](https://github.com/SOKTeam/S.O.K/commit/7afcd92379a3dc09ed4170dad971b1d3260cbd3d))
* **linux:** give unstyled text the theme colors ([2d1bc59](https://github.com/SOKTeam/S.O.K/commit/2d1bc5943c5c56728d398c28b12620a0acbcec38))
* **linux:** ship the X11 helper libraries and unpack appimagetool ([c68e83e](https://github.com/SOKTeam/S.O.K/commit/c68e83e103489b8530c64d6d08cf35dfa37a77c9))
* **organize:** list the files of a source folder in order ([64d4382](https://github.com/SOKTeam/S.O.K/commit/64d438227a80a40aadd4018f5f907d4092924d94))
* **ui:** color the home subtitle with the theme ([7ecbc4b](https://github.com/SOKTeam/S.O.K/commit/7ecbc4b857d1862cfe3524149340f6be0c3490fc)), closes [#8A8A8E](https://github.com/SOKTeam/S.O.K/issues/8A8A8E)
* **ui:** draw search results whose date or title is null ([9b68a7a](https://github.com/SOKTeam/S.O.K/commit/9b68a7a100b9f37df3be55221f8ae0ed08392935))
* **ui:** run worker callbacks in the GUI thread ([a9a438e](https://github.com/SOKTeam/S.O.K/commit/a9a438e8d7b66d2e8af64ab1087fa40111a2ad2b))
* **ui:** stop the app from aborting while search results reload ([f564870](https://github.com/SOKTeam/S.O.K/commit/f5648708766371513962bb76593aa978f8932f91))
* **video:** name episodes in the language chosen in settings ([aa08275](https://github.com/SOKTeam/S.O.K/commit/aa08275a61d0a514fc4207f2ceb521857887cfab))
* **windows:** name the installer with a three-part version ([31a874d](https://github.com/SOKTeam/S.O.K/commit/31a874dd77758679e604d86cbc021f02c77ff683))


### Features

* **linux:** add S.O.K to the applications menu ([902dccd](https://github.com/SOKTeam/S.O.K/commit/902dccdba786a0acc91a9b895aa1d2bb6cef4648))
* **linux:** attach the AppImages to each release ([3034799](https://github.com/SOKTeam/S.O.K/commit/3034799ec01e2fe93e1ea0169f4d8fc7c0641920))
* **linux:** build an AppImage on GitHub Actions ([5a3b67d](https://github.com/SOKTeam/S.O.K/commit/5a3b67dc5a1ab1c405e3334d0237719259d18710))
* **linux:** build an arm64 AppImage too ([e404251](https://github.com/SOKTeam/S.O.K/commit/e404251e28c290692300c55da1ba18dac59fa55a))
* **linux:** bundle Inter, add the app icon and desktop entry ([ecb70d0](https://github.com/SOKTeam/S.O.K/commit/ecb70d078f07f3e96fdb1823112a8477ecd64e07))
* **linux:** list the mounted disks on the home page ([5b04f42](https://github.com/SOKTeam/S.O.K/commit/5b04f4273a4613956e9617498d1a1f61ad68dc35))
* **linux:** move and resize the frameless window through the system ([6496d5c](https://github.com/SOKTeam/S.O.K/commit/6496d5cbd906ae28dbafb3e48d728347377f10ea))
* **linux:** store user data and logs in XDG folders ([cff5c25](https://github.com/SOKTeam/S.O.K/commit/cff5c256cbc8c8c2d4ebf83d26b26e27206cb230))
* **linux:** update the AppImage in place ([7e87296](https://github.com/SOKTeam/S.O.K/commit/7e87296a93969f1353a128a934bb97821e9a4927))


### Performance Improvements

* **ui:** download each search poster only once ([10431eb](https://github.com/SOKTeam/S.O.K/commit/10431ebd6d80c8912d3ea0d7dfd6a729f8d82532))

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
