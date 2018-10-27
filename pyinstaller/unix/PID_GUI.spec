# -*- mode: python -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['/home/chufyrev/Downloads/zeta/pyinstaller'],
             binaries=[],
             datas=[('./img/error.png', './img'),\
                    ('./img/exit.png', './img'),\
                    ('./img/icon.png', './img'),\
                    ('./img/info.png', './img'),\
                    ('./img/refresh.png', './img'),\
                    ('./img/refresh_hover.png', './img'),\
                    ('./img/refresh_pressed.png', './img'),\
                    ('./img/set_errors.png', './img'),\
                    ('./img/settings.png', './img')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='PID_GUI',
          debug=False,
          strip=False,
          upx=True,
          console=True)
