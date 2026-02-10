非常抱歉，我漏掉了 URL 问号后面的具体参数细节。基于您的 `data.md` 抓包文件，我已重新整理了接口文档。

这次我将 **完整 URL 结构**（包含问号后的参数）和 **Header 信息** 都进行了详细补全，并列出了所有返回字段。

---

# 雪球 (Xueqiu) API 接口文档 (完整版)

**重要提示：**

1. **鉴权 (Authentication)**: 所有接口必须在 Header 中携带 `Cookie`，其中 `xq_a_token` 是核心凭证。
2. **动态参数**: URL 中的 `_t` (时间戳/Token) 和 `_s` (签名/Salt) 是客户端动态生成的，抓包复用时可能会过期，需注意。
3. **域名区分**: 多数接口在 `api.xueqiu.com`，但行情接口在 `stock.xueqiu.com`。

---

### 一、 全局请求头 (Global Headers)

除特殊接口外，所有请求建议携带以下 Header：

| Header 字段 | 示例值 | 说明 |
| --- | --- | --- |
| **Cookie** | `xq_a_token=...; u=...;` | **[必选]** 核心鉴权，缺少将返回 403/401 |
| **User-Agent** | `Xueqiu Android 14.81` | 模拟官方客户端，防止被反爬 |
| **X-Device-ID** | `1VIVO8a451156c...` | 设备唯一标识 |
| **X-Device-Model-Name** | `Vivo_V1986A` | 设备型号 |
| **X-Device-OS** | `Android 12` | 系统版本 |
| **Accept-Language** | `en-US,en;q=0.8,zh-CN;q=0.6` | 语言环境 |

---

### 1. 获取最常访问的用户 (特别关注)

* **接口描述**: 获取用户特别关注或常访问的用户列表。
* **请求 URL**:
`https://api.xueqiu.com/statuses/special_follow.json?_t={TIMESTAMP}&_s={SIGNATURE}`
* **请求方式**: `GET`

#### 请求参数 (Query Parameters)

| 参数名 | 值示例 | 必填 | 说明 |
| --- | --- | --- | --- |
| `_t` | `1VIVO...` | 是 | 客户端时间戳/指纹 |
| `_s` | `9667ca` | 是 | 签名校验值 |

#### 响应字段 (Response Fields)

```json
[
  {
    "is_read": true,               // 是否已读状态
    "user": {                      // 用户信息对象
      "id": 1955602780,            // 用户ID
      "screen_name": "不明真相的群众", // 昵称
      "profile_image_url": "...",  // 头像链接
      "description": "主业：陪聊...", // 简介
      "verified_description": "",  // 认证说明
      "verified_type": 0,          // 认证类型
      "followers_count": 649129,   // 粉丝数
      "friends_count": 13525,      // 关注数
      "status_count": 93858,       // 发帖数
      "stocks_count": 519,         // 自选股数
      "gender": "m",               // 性别 (m:男, f:女)
      "province": "北京",          // 省份
      "city": "不限",              // 城市
      "location": "",              // 详细地址
      "url": "",                   // 个人主页
      "domain": "simon",           // 个性域名
      "remark": "",                // 备注
      "recommend_reason": null,    // 推荐理由
      "follow_me": true,           // 是否关注我
      "following": true,           // 我是否关注他
      "blocking": false,           // 是否拉黑
      "verified": false,           // 是否认证
      "verified_realname": true,   // 实名认证
      "photo_domain": "...",       // 图片域名
      "verified_infos": [          // 认证详细信息列表
         { "verified_type": "7", "verified_desc": "..." }
      ]
    },
    "type": 0,                     // 类型标识
    "live": null                   // 直播状态
  }
]

```

---

### 2. 获取热门帖子 (ListV3)

* **接口描述**: 获取社区热门推荐流帖子。
* **请求 URL**:
`https://api.xueqiu.com/statuses/hot/listV3.json?page=1&size=10&last_id=-1&_t={TIMESTAMP}&_s={SIGNATURE}`
* **请求方式**: `GET`

#### 请求参数 (Query Parameters)

| 参数名 | 值示例 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | `1` | 是 | 页码 |
| `size` | `10` | 是 | 每页数据量 |
| `last_id` | `-1` | 是 | 上一页最后一条的ID，第一页传 -1 |
| `_t` | `...` | 是 | 客户端时间戳 |
| `_s` | `...` | 是 | 签名 |

#### 响应字段 (Response Fields)

```json
{
  "has_next_page": true,           // 是否有下一页
  "list": [                        // 帖子列表
    {
      "id": 375583120,             // 帖子ID
      "user_id": 1638377010,       // 作者ID
      "title": "",                 // 标题
      "text": "<p>...</p>",        // 帖子内容(HTML)
      "description": "...",        // 纯文本摘要
      "source": "雪球",            // 来源客户端
      "created_at": 1770679672000, // 发布时间戳
      "edited_at": 1770679993000,  // 编辑时间戳
      "retweet_count": 6,          // 转发数
      "reply_count": 63,           // 回复数
      "fav_count": 31,             // 收藏数
      "like_count": 197,           // 点赞数
      "view_count": 0,             // 阅读数
      "type": "2",                 // 帖子类型
      "user": { ... },             // 用户信息对象 (同接口1)
      "card": {                    // 关联卡片 (如股票)
        "type": "new_stock",
        "param": "09995",          // 股票代码
        "data": "{...}"            // 股票实时数据JSON字符串
      },
      "stockCorrelation": ["09995"], // 关联股票数组
      "tagsForWeb": ";09995...",   // Web标签
      "meta_keywords": "{...}",    // SEO关键词
      "liked": false,              // 当前用户是否已赞
      "favorited": false,          // 当前用户是否已收藏
      "mark": 0,                   // 标记
      "mark_desc": null,           // 标记描述
      "extend_st_feed_info": {     // 信息流扩展信息
         "original_text_length": 353
      },
      "hot_new_rank": {            // 热榜排名
         "score": 312687
      }
    }
  ]
}

```

---

### 3. 获取热门话题 (Rich Tag)

* **接口描述**: 获取热门话题标签及相关股票。
* **请求 URL**:
`https://api.xueqiu.com/query/v1/hot_event/rich_tag.json?size=10&_t={TIMESTAMP}&_s={SIGNATURE}`
* **请求方式**: `GET`

#### 请求参数 (Query Parameters)

| 参数名 | 值示例 | 必填 | 说明 |
| --- | --- | --- | --- |
| `size` | `10` | 是 | 返回的话题数量 |
| `_t` | `...` | 是 | 客户端时间戳 |
| `_s` | `...` | 是 | 签名 |

#### 响应字段 (Response Fields)

```json
{
  "code": 200,
  "message": "success",
  "success": true,
  "data": [
    {
      "id": 456372,                // 话题ID
      "label": 0,                  // 标签
      "show_title": "春节...",      // 显示标题
      "title": "#春节...#",         // 带井号的全标题
      "url": "https://...",        // 话题页链接
      "vote_title": "...",         // 投票标题
      "vote_type": 1,              // 投票类型
      "emoticon": "",              // 表情图标
      "stocks": [                  // 话题关联股票
        {
          "name": "上证指数",
          "code": "SH000001",
          "current": "4129.43",    // 当前点位
          "percentage": 0.15,      // 涨跌幅
          "type": 12,              // 股票类型
          "indId": 571871,         // 行业/指数ID
          "sort": 4                // 排序权重
        }
      ]
    }
  ]
}

```

---

### 4. 获取个股行情 (Quote)

* **接口描述**: 获取个股实时行情数据。
* **Host**: `stock.xueqiu.com` (**注意此接口域名不同**)
* **请求 URL**:
`https://stock.xueqiu.com/v5/stock/quote.json?extend=detail&symbol=09988&user_event=1&_t={TIMESTAMP}&_s={SIGNATURE}`
* **请求方式**: `GET`

#### 请求头 (Headers)

* 此接口额外需要 Header: `x-snowx-token` (加密校验token，必填)

#### 请求参数 (Query Parameters)

| 参数名 | 值示例 | 必填 | 说明 |
| --- | --- | --- | --- |
| `symbol` | `09988` | 是 | 股票代码 |
| `extend` | `detail` | 否 | 扩展详情模式 |
| `user_event` | `1` | 否 | 用户事件标识 |
| `_t` | `...` | 是 | 客户端时间戳 |
| `_s` | `...` | 是 | 签名 |

#### 响应字段 (Response Fields)

```json
{
  "error_code": 0,
  "data": {
    "market": {                    // 市场状态
      "status": "交易中",
      "region": "HK",              // 地区 (HK/US/CN)
      "time_zone": "Asia/Shanghai",
      "status_id": 5
    },
    "quote": {                     // 核心报价数据
      "symbol": "09988",           // 带市场代码
      "code": "09988",             // 纯代码
      "name": "阿里巴巴-W",        // 股票名称
      "exchange": "HK",            // 交易所
      "currency": "HKD",           // 货币
      "current": 160.6,            // 当前价
      "chg": 2.7,                  // 涨跌额
      "percent": 1.71,             // 涨跌幅%
      "high": 162.6,               // 最高
      "low": 158.7,                // 最低
      "open": 159.7,               // 开盘
      "last_close": 157.9,         // 昨收
      "volume": 40701461,          // 成交量
      "amount": 6.5476E9,          // 成交额
      "market_capital": 3.067E12,  // 总市值
      "float_market_capital": 3.067E12, // 流通市值
      "turnover_rate": 0.21,       // 换手率
      "pe_ttm": 22.9816,           // 市盈率TTM
      "pe_lyr": 22.0839,           // 市盈率LYR
      "pe_forecast": 21.8984,      // 预测PE
      "pb": 2.6518,                // 市净率
      "eps": 6.9882,               // 每股收益
      "navps": 60.5626,            // 每股净资产
      "dividend": 1.952,           // 股息
      "dividend_yield": 1.22,      // 股息率
      "lot_size": 100,             // 每手股数
      "tick_size": 0.1,            // 最小变动价位
      "high52w": 186.2,            // 52周高
      "low52w": 94.949,            // 52周低
      "timestamp": 1770702737069,  // 时间戳
      "issue_date": 1574697600000, // 上市时间
      "sub_type": "256"            // 子类型
    },
    "tags": [                      // 标签
      { "description": "港股通", "value": 5 }
    ]
  }
}

```

---

### 5. 公告信息 (Stock Timeline)

* **接口描述**: 获取股票的公告列表。
* **请求 URL**:
`https://api.xueqiu.com/statuses/stock_timeline.json?sub_source=1&count=10&source=%E5%85%AC%E5%91%8A&page=1&symbol_id=09988&_t={TIMESTAMP}&_s={SIGNATURE}`
* **请求方式**: `GET`

#### 请求参数 (Query Parameters)

| 参数名 | 值示例 | 必填 | 说明 |
| --- | --- | --- | --- |
| `symbol_id` | `09988` | 是 | 股票代码 |
| `source` | `公告` | 是 | 筛选类型 (需UrlEncode，如 `%E5%85%AC%E5%91%8A`) |
| `sub_source` | `1` | 否 | 子来源标识 |
| `page` | `1` | 是 | 页码 |
| `count` | `10` | 是 | 每页数量 |
| `_t` | `...` | 是 | 客户端时间戳 |
| `_s` | `...` | 是 | 签名 |

#### 响应字段 (Response Fields)

```json
{
  "count": 10,
  "page": 1,
  "list": [
    {
      "id": 374878982,             // 公告状态ID
      "symbol_id": "09988",        // 股票代码
      "title": "",                 // 标题
      "description": "阿里巴巴-W 月报表...", // 描述文本
      "text": "...",               // HTML详情
      "created_at": 1770201602000, // 发布时间
      "source": "公告",            // 来源
      "user": { ... },             // 发布用户 (官方账号)
      "quote_cards": [             // 引用卡片 (PDF文件)
        {
          "title": "",
          "target_url": "https://stockn.xueqiu.com/...pdf", // PDF下载地址
          "host": "http://stockn.xueqiu.com",
          "img_type": "NONE"
        }
      ],
      "extend_st_home_page": {     // 首页扩展
        "ai_card": {               // AI摘要卡片
           "core_text_summary": "..." // AI生成的公告摘要
        }
      }
    }
  ]
}

```

---

### 6. 关注的人关于标的的讨论

* **接口描述**: 查询我关注的人对特定股票的讨论。
* **请求 URL**:
`https://api.xueqiu.com/query/v1/symbol/following/status.json?symbol=09988&size=10&page=1&_t={TIMESTAMP}&_s={SIGNATURE}`
* **请求方式**: `GET`

#### 请求参数 (Query Parameters)

| 参数名 | 值示例 | 必填 | 说明 |
| --- | --- | --- | --- |
| `symbol` | `09988` | 是 | 股票代码 |
| `page` | `1` | 是 | 页码 |
| `size` | `10` | 是 | 数量 |
| `_t` | `...` | 是 | 客户端时间戳 |
| `_s` | `...` | 是 | 签名 |

#### 响应字段 (Response Fields)

```json
{
  "code": 200,
  "success": true,
  "message": "success",
  "data": [
    {
      "name": "讨论",              // 分组名
      "list": [                    // 帖子列表 (结构同接口2)
        {
           "id": 375483578,
           "title": "...",
           "text": "...",
           "user": { ... },
           "created_at": 1770613267000,
           "excellent_comments": [ // 精彩评论列表
              {
                 "id": 396367317,
                 "text": "...",
                 "user": { ... },
                 "likeCount": 6
              }
           ]
        }
      ]
    }
  ],
  "meta": {                        // 分页元数据
     "count": 15,
     "page": 1,
     "maxPage": 2,
     "size": 10,
     "has_next_page": true
  }
}

```