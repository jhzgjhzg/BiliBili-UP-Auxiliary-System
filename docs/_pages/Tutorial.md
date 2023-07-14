---
title: Tutorial
author: jhzg
date: 2023-07-12
category: doc
layout: post
---

> This will introduce the functions implemented by this library.
{: .block-tip }

## Configuration

1. Set the data storage address for recorded data.
2. Set the ffmpeg path for downloading video or audio. The download method for ffmpeg can refer to: 
   [Windows Installation ffmpeg](https://blog.csdn.net/weixin_71624489/article/details/128929228), 
   [macOS Installation ffmpeg](https://blog.csdn.net/qq_45956730/article/details/125301182).
3. Set the mark for marking the danmaku in the live broadcast room.
4. Set the language for output prompts.

## Login

1. Most of the functions in this library do not require logging into a Bilibili account, but live-streaming related 
   functions require logging in. Recommend using scanned QR code to log in.
2. You can log in by scanning the QR code, password, and verification code.
3. Alternatively, you can directly specify the account parameters, which can be obtained by referring to: 
   [Account parameters](https://nemo2011.github.io/bilibili-api/#/get-credential).

> The login information is stored locally and there is no risk of leakage.
{: .block-tip }

## Video

1. Generate a word cloud image of the video, and you can select the content of the word cloud image (comments, danmaku, 
   both), content depth (whether to include secondary comments), and word cloud image mask.
2. Download video (.mp4) or audio (.mp3).
3. Predict the future data of the newly released video, you can choose to use the primary model or a separate 
   partition model. (In preparation)

## User

1. Record the current number of followers, members of the guards, and charging members of the user.
2. Generate a change curve for the above data. This function requires sufficient data, and if the amount of data is 
   insufficient, it cannot be generated. (In preparation)
3. Send a private message to the guards to collect the address.
4. Collect the address information from the reply.

## Live

1. Monitor live-streaming data, record danmaku, gifts, SC, popularity.
2. Record the danmaku with marks at the beginning or end sent in the live broadcast room.
3. Analyze live-streaming data, generate multiple types of danmaku quantity change charts, revenue change 
   charts, revenue distribution pie charts, live-streaming popularity change charts, and danmaku word cloud 
   charts.
4. Generate live-streaming slicing suggestions from the danmaku with marks at the beginning or end.
