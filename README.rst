Boxnyaはマルチインプット, マルチアウトプットな汎用通知システムです.

Python 2.6以上が必要です. Python 3.xはサポートしていません.

Boxnyaとは
=============

Boxnyaは, SNSなどのネット上の情報をあらゆる端末に通知することを目的としたシステムです.

これらの機能は全てプラグインで実現されており, 指定されたフォルダにプラグインを入れて設定を書くだけで使うことができます.

使い方
=============

Boxnyaフォルダを任意のディレクトリに置いて, コマンドラインからBoxnya/src/boxnya.pyを起動します.

プラグインは, Boxnya/src/lib/input, output, filterフォルダに入れ, 必要に応じて設定を書きます.

設定
=============

Boxnya/src/settings.pyに設定を書きます.

Boxnya/src/settings.py.example のを参照してください.

プラグインの役割
=============

Inputプラグイン
--------------------

ネット等から情報を取得してきます. twitterの場合userstreamを読み続けます.

Filterプラグイン
--------------------

Inputから受け取った情報をフィルタリングします. 

Outputプラグイン
--------------------

InputあるいはFilterから受け取った情報を, Boxnya以外のシステムへの送り出します.

機能
==============

Boxnyaは最低限の機能としてtwitter, fav, @, RT, DM, follow, listed, エゴサーチの通知を提供します.

他の雑多なプラグインはboxnya-pluginリポジトリで公開しています.

Twitter Input
------------------

設定に書いたユーザの数だけuserstreamを読み取り続けます.

Egosearch Filter
------------------

設定にかかれたスクリーンネームのユーザに対してfav等の通知を行います.

正規表現を設定することでエゴサーチも可能です.

オプションとして, 非公式RTを非通知にする機能や, favテロ, 複数アカウント間でのfav同期などがあります.

Im.kayac Output
------------------

im.kayac.comを利用してiPhoneへのPush通知を行います.

また, im.kayac.comで設定をすればgoogle talkへも同時に通知できます.
