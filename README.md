# BiliBili-UP-Auxiliary-System

# Introduction
Assist Bilibili users in recording and analyzing live streaming data and video data.\
This module implements the following functions:
- Monitor the data of the live broadcast room.
- Analyze and process live-streaming room data, generate various analysis graphs, and provide suggestions for 
  live-streaming slicing.
- Generate a word cloud image of the video, which can include content as desired.
- Download the video.
- Predict various data for publishing videos. (In development)
- Record the number of users' followers, etc., and generate a change curve to predict changes over a period of time in the future. (In development)
- Send a private message to the guard to collect the address and collect the address information. (requires logging into the Bilibili account)
- ...

> **Warning**\
> This module is only for learning and testing purposes.
> Any consequences caused by unauthorized use of this module are not related to the developer.
> If there is any infringement, please contact the developer to delete the relevant content.

# Using Tutorials
## Module Installation:
### Preparation environment
This module depends on Python, so you need to install Python on your computer first.\
Recommend using Miniconda to manage Python environments.\
[Windows Installation Miniconda Guide](https://blog.csdn.net/weixin_43828245/article/details/124768518) \
[macOS Installation Miniconda Guide](https://blog.csdn.net/tangsiqi130/article/details/130112475)
> Recommended to use version 3.9 and above of Python, and lower versions have not been tested!

### Install module
After installing Miniconda, you can use the following command to install the module:
```shell
pip install bili-uas
```

## Module Usage:
If you want to monitor the data of a live broadcast room, you can execute such commands in the cmd or terminal:
```shell
bili-config --work_dir <YOUR/PATH/TO/STORE/DATA> --mark <YOUR/MARK>
bili-live monitor --live_id <LIVE/ROOM/ID> --forever False
```

If you want to generate a comment cloud map for a certain video, you can execute this command in cmd or terminal:
```shell
bili-config --work_dir <YOUR/PATH/TO/STORE/DATA>
bili-video word_cloud --video_id <VIDEO/ID>
```

If you want to download a certain video, you can execute this command in cmd or terminal:
```shell
bili-config --work_dir <YOUR/PATH/TO/STORE/DATA> --ffmpeg <YOUR/PATH/TO/FFMPEG>
bili-video download --video_id <VIDEO/ID>
```

Login to Bilibili account:
```shell
bili-login --mode 2
```

> **Note**\
> Some functions require logging into a Bilibili account.\
> The login information will be stored locally without any risk of leakage.

For a more detailed command line introduction, please refer to the documentation.

# FAQ
**Q: What to do when encountering a bug.**

F: You can submit an issue on this page. If you do not know how to submit an issue, you can contact me via email or QQ.

**Q: I need a feature that is currently not available.**

F: You can describe your requirements by submitting an issue, email, or QQ, but developers may not have the time to 
write this feature. 
You can also implement it yourself and initiate a Pull request.

**Q: I want to contribute code to this project.**

F: You can fork this project and implement the feature you want to implement, and then initiate a Pull request to main.
Contribution guidelines: [CONTRIBUTING.md](https://github.com/nemo2011/bilibili-api/blob/main/.github/CONTRIBUTING.md)

# Documentation
In preparation...

# Appendix
**Contact developer:** 
- email: jhzg02200059@163.com
- QQ: 3465986375

**Appreciate developer:**\
If you think this module is good, you can give it a star or buy a cup of coffee for the developer：
<img alt="Buy me a coffee" height="300" src="https://github.com/jhzgjhzg/BiliBili-UP-Auxiliary-System/blob/main/design/appreciation.jpg" width="300"/>

