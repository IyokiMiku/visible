# get-question-list API 参考

## 基本信息

| 项目 | 值 |
|------|---|
| 接口 | `POST https://yanyi.zxxk.com/11181/18001/api-question/v1/question/get-question-list` |
| Content-Type | `application/json` |
| 鉴权 | Header: `Cookie` + `appKey` + `sign`（三者缺一不可） |
| 默认 structFormat | `HTML`（比 QML 更规整易处理） |
| 默认 formatEnum | `LATEX` |

## 鉴权

生产环境需要三个请求头，**缺一不可**：

| Header | 说明 |
|--------|------|
| Cookie | 从浏览器登录 zxxk.com 后的 JSESSIONID 等，有效期有限 |
| appKey | 应用密钥 `4f2a82224eb140e5964d0891a1affcc6`（固定值） |
| sign | 签名 `dfe533d82b4e5ee8aa390b1f775537ae`（固定值） |

```bash
curl ... \
  --header 'Cookie: acw_tc=...; JSESSIONID=...; ...' \
  --header 'appKey: 4f2a82224eb140e5964d0891a1affcc6' \
  --header 'sign: dfe533d82b4e5ee8aa390b1f775537ae' \
  --data '{...}'
```

> ⚠️ Cookie 会过期。过期后需从浏览器重新获取并更新脚本中的 `DEFAULT_COOKIE`。

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bankIds | List\<Integer\> | **否**（可选，不传即搜全库） | 子库ID，装备制造类可不传 |
| courseId | Integer | 否 | 课程ID，见 `course_type_mapping.md` |
| typeIds | List\<String\> | 否 | 题型ID，见 `course_type_mapping.md` |
| kpointIds | List\<Integer\> | 否 | 知识点ID列表 |
| primaryKPointIds | List\<Integer\> | 否 | 主知识点ID列表 |
| catalogIds | List\<String\> | 否 | 章节ID列表 |
| difficultyLowLimit | Double | 否 | 难度下限 (0=最难, 1=最易) |
| difficultyUpLimit | Double | 否 | 难度上限 |
| pageIndex | Integer | 是 | 页码，从 1 开始 |
| pageSize | Integer | 是 | 每页条数 |
| fields | List\<String\> | **是** | 返回字段列表，至少含 question_id/stem/answer/explanation/difficulty/course_id/type_id/kpointIds |
| structFormat | Enum | 否 | `QML` / `HTML`，默认 QML |
| formatEnum | Enum | 否 | `LATEX` / `SVG`，默认 LATEX |

## 难度映射表

| 名称 | API调用方式 | 范围说明 |
|------|-----------|---------|
| 容易 | `difficultyLowLimit=0.8, difficultyUpLimit=1.0` | 0.8 ~ 1.0 |
| 较易 | `difficultyLowLimit=0.6, difficultyUpLimit=0.8` | 0.6 ~ 0.8 |
| 一般/适中 | `difficultyLowLimit=0.4, difficultyUpLimit=0.6` | 0.4 ~ 0.6 |
| 较难 | `difficultyLowLimit=0.2, difficultyUpLimit=0.4` | 0.2 ~ 0.4 |
| 困难 | `difficultyLowLimit=0.0, difficultyUpLimit=0.2` | 0.0 ~ 0.2 |

> 注意：difficulty 值越小越难（0=极难, 1=极易）。LowLimit ≤ UpLimit。

## 返回字段说明

| 字段 | 说明 |
|------|------|
| questionId | 试题唯一ID |
| courseId | 课程ID |
| typeId | 题型编码 |
| difficulty | 难度值，高频浮点数 |
| stem | 题干，QML格式XML |
| answer | 答案，QML格式XML |
| explanation | 解析，QML格式XML |
| kpointIds | 试题整体知识点ID列表 |
| subQuestionProps | 子题知识点绑定 |
| tagIds | 标签: "1"=新题, "2"=优质题 |
| status | 状态: 1=正常 |
| media | 含媒体文件: 0=无, 1=有 |
| year | 试题年份 |
| sourceId | 来源编号 |

## 调用模板

### 单题型查询

```python
import requests

resp = requests.post(
    "https://yanyi.zxxk.com/11181/18001/api-question/v1/question/get-question-list",
    json={
        "bankIds": [28],
        "courseId": COURSE_ID,
        "typeIds": ["TYPE_ID"],
        "difficultyLowLimit": 0.4,
        "difficultyUpLimit": 0.6,
        "pageIndex": 1,
        "pageSize": 5,
        "fields": ["question_id","stem","answer","explanation","difficulty","course_id","type_id","kpointIds"]
    }
)
data = resp.json()
```

### 不限难度查询

```python
resp = requests.post(
    "https://yanyi.zxxk.com/11181/18001/api-question/v1/question/get-question-list",
    json={
        "bankIds": [28],
        "courseId": COURSE_ID,
        "typeIds": ["TYPE_ID"],
        "pageIndex": 1,
        "pageSize": 10,
        "fields": ["question_id","stem","answer","explanation","difficulty","course_id","type_id","kpointIds"]
    }
)
```

### 多题型查询

```python
resp = requests.post(
    "https://yanyi.zxxk.com/11181/18001/api-question/v1/question/get-question-list",
    json={
        "bankIds": [28],
        "courseId": COURSE_ID,
        "typeIds": ["TYPE_ID_1", "TYPE_ID_2", "TYPE_ID_3"],
        "pageIndex": 1,
        "pageSize": 20,
        "fields": ["question_id","stem","answer","explanation","difficulty","course_id","type_id","kpointIds"]
    }
)
```

## 注意事项

1. **fields 必填**: 不传 fields 将报 400
2. **difficulty 方向**: 值越小越难，lowLimit ≤ upLimit
3. **分页**: totalCount 可能不准，以实际返回条数为准
4. **QML 格式**: stem/answer/explanation 返回 QML（类 HTML+MathML），含 `<stem>`, `<sq>`, `<math>`, `<img>` 等标签，公式用 MathML，图片用外链 URL
5. **typeId 格式**: 每个课程有独立的题型编号体系，必须从 `references/categories/{大类}.md` 读取，不同课程间不通用
