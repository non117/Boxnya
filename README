Boxnyaはマルチインプット, マルチアウトプットの汎用通知システムです.

Python 2.6以上が必要です. Python 3.xはサポートしていません.

Boxnyaとは
===========

　Boxnyaは, SNSなどのネット上の情報をあらゆる端末に通知することを目的としたシステムです.

これらの機能は全てプラグインで実現されており, 指定されたフォルダにプラグインを入れて設定を書くだけで使うことができます.

使い方
===========

　Boxnyaフォルダを任意のディレクトリに置いて, コマンドラインからBoxnya/src/boxnya.pyを起動します.

プラグインは, Boxnya/src/lib/input, output, filterフォルダに入れ, 必要に応じて設定を書きます.

設定
===========

　Boxnya/src/settings.pyに設定を書きます.

Boxnya/src/settings.py.example のを参照してください.

プラグインの役割
===========

 * Inputプラグイン

ネット等から情報を取得してきます. twitterの場合userstreamを読み続けます.

 * Filterプラグイン

Inputから受け取った情報をフィルタリングします. 
twitterで複数アカウントを運用する場合などはまとめてフィルタリングすることができます.

* Outputプラグイン

InputあるいはFilterから受け取った情報を, Boxnya以外のシステムへの送り出します.
twitterの場合には, Growlやim.kayac.comにデータを通知します.