=== なにができるの？
リプライ、ふぁぼられ、公式RT、キーワードヒットの通知が出来ます。
im.kayacを入れたiPhoneにpushすることもできます。
Androidはよくわかりません。

=== つかいかた
1. settings.yamlに色々書きましょう。
    screen_name : スクリーンネーム
    reg_exp : キーワード(正規表現)
    im_id : im.kayacのid
    im_pswd : im.kayacのパスワード
    im_sig : im.kayacの秘密鍵
  ※注意：utf-8で保存しないと動きません。
パスワードと秘密鍵は空でも大丈夫です。
2. pythonをインストール
3. easy_installをインストール
4.
easy_install pyyaml
easy_install simplejson
   をシェルやコマンドプロンプトで実行。
5. python boxnya.py [USER]
6. oauth認証してください。
7. 放置しましょう。
  ※注意：yamlファイルはconf/[USER]ディレクトリに置いてください。

python boxnya.py -h でヘルプ出るから見てね。