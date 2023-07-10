---
layout: home
title: BiliBili UP Auxiliary System
permalink: /
---

Assist Bilibili users in recording and analyzing live streaming data and video data.

## Source Code

GitHub Warehouse: [BiliBili-UP-Auxiliary-System
](https://github.com/jhzgjhzg/BiliBili-UP-Auxiliary-System
)

[![Stable Version](https://img.shields.io/pypi/v/bili-uas?label=PyPI)](https://pypi.org/project/bili-uas/)
[![LICENSE](https://img.shields.io/badge/LICENSE-GPLv3+-red)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9|3.10|3.11-blue)](https://www.python.org)

## What can bili-uas do
### Video
- [x] Download video
- [x] Download audio
- [x] Generate a word cloud image
- [ ] Predicting various data for publishing videos
- [ ] ...

### User

- [x] Get user data
- [ ] Generate data change image and predict future changes
- [x] Send a private message for collecting addresses to members of the Grand Navigation Group
- [x] Collect address information from private messages
- [ ] ...

### Live

- [x] Monitor live data, including gifts, sc, danmu, popularity, etc.
- [x] Capture danmu with custom marks
- [x] Generate data analysis image
- [x] Provide video slicing suggestions
- [ ] ...

> **Warning**\
> This library is only for learning and testing purposes.
> Any consequences caused by unauthorized use of this module are not related to the developer.
> If there is any infringement, please contact the developer to delete the relevant content.
{: .block-warning }


## How to Get Started

### Preparation environment

Bili-uas requires `python>=3.9`, and lower versions have not been tested.\
We recommend using Conda to manage dependencies. Make sure to install Conda before proceeding.\
[Windows Installation Miniconda Guide](https://blog.csdn.net/weixin_43828245/article/details/124768518) \
[macOS Installation Miniconda Guide](https://blog.csdn.net/tangsiqi130/article/details/130112475)
```shell
conda create -n bili-uas -y python=3.9
conda activate bili-uas
python -m pip install --upgrade pip
```

### Installation

Easy option:
```shell
pip install --upgrade bili-uas
```

**OR** if you want the latest and greatest:
```shell
git clone https://github.com/jhzgjhzg/BiliBili-UP-Auxiliary-System.git
cd BiliBili-UP-Auxiliary-System
pip install --upgrade pip setuptools
pip install -e .
```

> **Note**\
> This library is frequently updated. Please confirm that you are using the latest or stable version before using it.
{: .block-tip }

### Using python packages

```python
import Bili_UAS
```

## FAQ
**Q: What to do when encountering a bug.**

F: You can submit an issue on this page. If you do not know how to submit an issue, you can contact me via email or QQ.

**Q: I need a feature that is currently not available.**

F: You can describe your requirements by submitting an issue, email, or QQ, but developers may not have the time to 
write this feature. 
You can also implement it yourself and initiate a Pull request.

**Q: I want to contribute code to this project.**

F: You can fork this project and implement the feature you want to implement, and then initiate a Pull request to main.
Contribution guidelines: [CONTRIBUTING.md](https://github.com/nemo2011/bilibili-api/blob/main/.github/CONTRIBUTING.md)

## License
This library uses the [GNU General Public License v3.0](
https://www.gnu.org/licenses/gpl-3.0.en.html
) license.

## Appendix
**Contact developer:** 
- email: jhzg02200059@163.com
- QQ: 3465986375

**Appreciate developer:**\
If you think this library is not bad, you can give it a star or buy a cup of coffee for the developer：
<img alt="Buy me a coffee" height="300" src="./design/main/appreciation.jpg" width="300"/>

