# -*- mode: python -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['/home/chufyrev/PycharmProjects/pid-gui'],
             binaries=[],
             datas=[('./img/eeprom.png', './img'),
                    ('./img/error.png', './img'),
                    ('./img/exit.png', './img'),
                    ('./img/icon.png', './img'),
                    ('./img/info.png', './img'),
                    ('./img/play_pause.png', './img'),
                    ('./img/refresh.png', './img'),
                    ('./img/refresh_hover.png', './img'),
                    ('./img/refresh_pressed.png', './img'),
                    ('./img/restore.png', './img'),
                    ('./img/set_errors.png', './img'),
                    ('./img/settings.png', './img'),
                    ('./defaultSettings.json', '.')
                   ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='PID_controller_GUI',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
