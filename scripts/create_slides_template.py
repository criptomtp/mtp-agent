"""Create Google Slides template for MTP Fulfillment proposals."""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'researchagent-for-ff-mtp-e4ddbc60855c.json'

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
slides_service = build('slides', 'v1', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)

# Create presentation
presentation = slides_service.presentations().create(body={
    'title': 'MTP Fulfillment — Template'
}).execute()
presentation_id = presentation['presentationId']
print(f'Created: {presentation_id}')

# Make public for reading
drive_service.permissions().create(
    fileId=presentation_id,
    body={'type': 'anyone', 'role': 'reader'}
).execute()

# Get first slide ID
slide_id = presentation['slides'][0]['objectId']

# Color palette
PRIMARY = {'red': 0.098, 'green': 0.098, 'blue': 0.180}   # #191930
ACCENT =  {'red': 0.145, 'green': 0.588, 'blue': 0.745}   # #2596be
WHITE =   {'red': 1.0,   'green': 1.0,   'blue': 1.0}
LIGHT =   {'red': 0.96,  'green': 0.97,  'blue': 0.98}
DARK =    {'red': 0.10,  'green': 0.10,  'blue': 0.12}
GRAY =    {'red': 0.40,  'green': 0.40,  'blue': 0.45}

def pt(val):
    return {'magnitude': val, 'unit': 'PT'}

W = 9144000  # slide width EMU
H = 5143500  # slide height EMU

requests = []

# ============ SLIDE 1: COVER ============

# Dark background
requests.append({'updatePageProperties': {
    'objectId': slide_id,
    'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': PRIMARY}}}},
    'fields': 'pageBackgroundFill'
}})

# Left accent bar
requests.append({'createShape': {
    'objectId': 'slide1_accent',
    'shapeType': 'RECTANGLE',
    'elementProperties': {
        'pageObjectId': slide_id,
        'size': {'width': pt(8), 'height': pt(280)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(80), 'unit': 'PT'}
    }
}})
requests.append({'updateShapeProperties': {
    'objectId': 'slide1_accent',
    'shapeProperties': {
        'shapeBackgroundFill': {'solidFill': {'color': {'rgbColor': ACCENT}}},
        'outline': {'outlineFill': {'solidFill': {'color': {'rgbColor': ACCENT}}}, 'weight': pt(0)},
    },
    'fields': 'shapeBackgroundFill,outline'
}})

# MTP GROUP logo text
requests.append({'createShape': {
    'objectId': 'slide1_logo',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': slide_id,
        'size': {'width': pt(200), 'height': pt(30)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(80), 'unit': 'PT'}
    }
}})
requests.append({'insertText': {'objectId': 'slide1_logo', 'text': 'MTP GROUP'}})
requests.append({'updateTextStyle': {
    'objectId': 'slide1_logo',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': ACCENT}}, 'fontSize': pt(14), 'bold': True},
    'fields': 'foregroundColor,fontSize,bold'
}})

# Client name placeholder
requests.append({'createShape': {
    'objectId': 'slide1_client',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': slide_id,
        'size': {'width': pt(400), 'height': pt(50)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(130), 'unit': 'PT'}
    }
}})
requests.append({'insertText': {'objectId': 'slide1_client', 'text': '{{client_name}}'}})
requests.append({'updateTextStyle': {
    'objectId': 'slide1_client',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': WHITE}}, 'fontSize': pt(36), 'bold': True},
    'fields': 'foregroundColor,fontSize,bold'
}})

# Hook
requests.append({'createShape': {
    'objectId': 'slide1_hook',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': slide_id,
        'size': {'width': pt(400), 'height': pt(80)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(190), 'unit': 'PT'}
    }
}})
requests.append({'insertText': {'objectId': 'slide1_hook', 'text': '{{hook}}'}})
requests.append({'updateTextStyle': {
    'objectId': 'slide1_hook',
    'style': {
        'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 0.8, 'green': 0.85, 'blue': 0.9}}},
        'fontSize': pt(18),
    },
    'fields': 'foregroundColor,fontSize'
}})

# Subtitle
requests.append({'createShape': {
    'objectId': 'slide1_sub',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': slide_id,
        'size': {'width': pt(300), 'height': pt(30)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(300), 'unit': 'PT'}
    }
}})
requests.append({'insertText': {'objectId': 'slide1_sub', 'text': 'Комплексні логістичні рішення для e-commerce'}})
requests.append({'updateTextStyle': {
    'objectId': 'slide1_sub',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': GRAY}}, 'fontSize': pt(11)},
    'fields': 'foregroundColor,fontSize'
}})

# Execute slide 1
slides_service.presentations().batchUpdate(
    presentationId=presentation_id,
    body={'requests': requests}
).execute()
print('Slide 1 (Cover) created')

# ============ SLIDE 2: CLIENT INSIGHT ============
requests2 = []

requests2.append({'createSlide': {
    'objectId': 'slide2',
    'insertionIndex': 1,
    'slideLayoutReference': {'predefinedLayout': 'BLANK'},
}})
requests2.append({'updatePageProperties': {
    'objectId': 'slide2',
    'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': WHITE}}}},
    'fields': 'pageBackgroundFill'
}})

# Section title
requests2.append({'createShape': {
    'objectId': 'slide2_section',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide2',
        'size': {'width': pt(300), 'height': pt(20)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(40), 'unit': 'PT'}
    }
}})
requests2.append({'insertText': {'objectId': 'slide2_section', 'text': 'МИ РОЗУМІЄМО ВАШУ СПЕЦИФІКУ'}})
requests2.append({'updateTextStyle': {
    'objectId': 'slide2_section',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': ACCENT}}, 'fontSize': pt(10), 'bold': True},
    'fields': 'foregroundColor,fontSize,bold'
}})

# Client insight content
requests2.append({'createShape': {
    'objectId': 'slide2_insight',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide2',
        'size': {'width': pt(420), 'height': pt(100)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(70), 'unit': 'PT'}
    }
}})
requests2.append({'insertText': {'objectId': 'slide2_insight', 'text': '{{client_insight}}'}})
requests2.append({'updateTextStyle': {
    'objectId': 'slide2_insight',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': DARK}}, 'fontSize': pt(16)},
    'fields': 'foregroundColor,fontSize'
}})

# Left accent bar
requests2.append({'createShape': {
    'objectId': 'slide2_accent',
    'shapeType': 'RECTANGLE',
    'elementProperties': {
        'pageObjectId': 'slide2',
        'size': {'width': pt(5), 'height': pt(100)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(48), 'translateY': pt(70), 'unit': 'PT'}
    }
}})
requests2.append({'updateShapeProperties': {
    'objectId': 'slide2_accent',
    'shapeProperties': {
        'shapeBackgroundFill': {'solidFill': {'color': {'rgbColor': ACCENT}}},
        'outline': {'outlineFill': {'solidFill': {'color': {'rgbColor': ACCENT}}}, 'weight': pt(0)},
    },
    'fields': 'shapeBackgroundFill,outline'
}})

slides_service.presentations().batchUpdate(
    presentationId=presentation_id,
    body={'requests': requests2}
).execute()
print('Slide 2 (Client Insight) created')

# ============ SLIDE 3: PAIN POINTS ============
requests3 = []

requests3.append({'createSlide': {
    'objectId': 'slide3',
    'insertionIndex': 2,
    'slideLayoutReference': {'predefinedLayout': 'BLANK'},
}})
requests3.append({'updatePageProperties': {
    'objectId': 'slide3',
    'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': LIGHT}}}},
    'fields': 'pageBackgroundFill'
}})

# Section title
requests3.append({'createShape': {
    'objectId': 'slide3_section',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide3',
        'size': {'width': pt(400), 'height': pt(20)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(40), 'unit': 'PT'}
    }
}})
requests3.append({'insertText': {'objectId': 'slide3_section', 'text': 'ДЕ ЗАЗВИЧАЙ ВТРАЧАЄТЬСЯ ЕФЕКТИВНІСТЬ'}})
requests3.append({'updateTextStyle': {
    'objectId': 'slide3_section',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': ACCENT}}, 'fontSize': pt(10), 'bold': True},
    'fields': 'foregroundColor,fontSize,bold'
}})

# Pain points (3 placeholders)
for i in range(3):
    y_offset = 80 + i * 80
    # Pain title
    requests3.append({'createShape': {
        'objectId': f'slide3_pain{i}_title',
        'shapeType': 'TEXT_BOX',
        'elementProperties': {
            'pageObjectId': 'slide3',
            'size': {'width': pt(400), 'height': pt(25)},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(y_offset), 'unit': 'PT'}
        }
    }})
    requests3.append({'insertText': {'objectId': f'slide3_pain{i}_title', 'text': f'{{{{pain_{i}_title}}}}'}})
    requests3.append({'updateTextStyle': {
        'objectId': f'slide3_pain{i}_title',
        'style': {'foregroundColor': {'opaqueColor': {'rgbColor': DARK}}, 'fontSize': pt(14), 'bold': True},
        'fields': 'foregroundColor,fontSize,bold'
    }})
    # Pain description
    requests3.append({'createShape': {
        'objectId': f'slide3_pain{i}_desc',
        'shapeType': 'TEXT_BOX',
        'elementProperties': {
            'pageObjectId': 'slide3',
            'size': {'width': pt(400), 'height': pt(40)},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(y_offset + 25), 'unit': 'PT'}
        }
    }})
    requests3.append({'insertText': {'objectId': f'slide3_pain{i}_desc', 'text': f'{{{{pain_{i}_desc}}}}'}})
    requests3.append({'updateTextStyle': {
        'objectId': f'slide3_pain{i}_desc',
        'style': {'foregroundColor': {'opaqueColor': {'rgbColor': GRAY}}, 'fontSize': pt(11)},
        'fields': 'foregroundColor,fontSize'
    }})
    # Bullet icon
    requests3.append({'createShape': {
        'objectId': f'slide3_pain{i}_icon',
        'shapeType': 'ELLIPSE',
        'elementProperties': {
            'pageObjectId': 'slide3',
            'size': {'width': pt(8), 'height': pt(8)},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(63), 'translateY': pt(y_offset + 6), 'unit': 'PT'}
        }
    }})
    requests3.append({'updateShapeProperties': {
        'objectId': f'slide3_pain{i}_icon',
        'shapeProperties': {
            'shapeBackgroundFill': {'solidFill': {'color': {'rgbColor': ACCENT}}},
            'outline': {'outlineFill': {'solidFill': {'color': {'rgbColor': ACCENT}}}, 'weight': pt(0)},
        },
        'fields': 'shapeBackgroundFill,outline'
    }})

slides_service.presentations().batchUpdate(
    presentationId=presentation_id,
    body={'requests': requests3}
).execute()
print('Slide 3 (Pain Points) created')

# ============ SLIDE 4: WHY MTP ============
requests4 = []

requests4.append({'createSlide': {
    'objectId': 'slide4',
    'insertionIndex': 3,
    'slideLayoutReference': {'predefinedLayout': 'BLANK'},
}})
requests4.append({'updatePageProperties': {
    'objectId': 'slide4',
    'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': WHITE}}}},
    'fields': 'pageBackgroundFill'
}})

# Section title
requests4.append({'createShape': {
    'objectId': 'slide4_section',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide4',
        'size': {'width': pt(300), 'height': pt(20)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(40), 'unit': 'PT'}
    }
}})
requests4.append({'insertText': {'objectId': 'slide4_section', 'text': 'ЧОМУ МТП'}})
requests4.append({'updateTextStyle': {
    'objectId': 'slide4_section',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': ACCENT}}, 'fontSize': pt(10), 'bold': True},
    'fields': 'foregroundColor,fontSize,bold'
}})

# MTP fit text
requests4.append({'createShape': {
    'objectId': 'slide4_fit',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide4',
        'size': {'width': pt(420), 'height': pt(60)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(70), 'unit': 'PT'}
    }
}})
requests4.append({'insertText': {'objectId': 'slide4_fit', 'text': '{{mtp_fit}}'}})
requests4.append({'updateTextStyle': {
    'objectId': 'slide4_fit',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': DARK}}, 'fontSize': pt(14)},
    'fields': 'foregroundColor,fontSize'
}})

# Benefits (3 cards in a row)
for i in range(3):
    x_offset = 60 + i * 155
    # Card background
    requests4.append({'createShape': {
        'objectId': f'slide4_card{i}',
        'shapeType': 'ROUND_RECTANGLE',
        'elementProperties': {
            'pageObjectId': 'slide4',
            'size': {'width': pt(145), 'height': pt(120)},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(x_offset), 'translateY': pt(150), 'unit': 'PT'}
        }
    }})
    requests4.append({'updateShapeProperties': {
        'objectId': f'slide4_card{i}',
        'shapeProperties': {
            'shapeBackgroundFill': {'solidFill': {'color': {'rgbColor': LIGHT}}},
            'outline': {'outlineFill': {'solidFill': {'color': {'rgbColor': {'red': 0.9, 'green': 0.91, 'blue': 0.92}}}}, 'weight': pt(1)},
        },
        'fields': 'shapeBackgroundFill,outline'
    }})
    # Benefit title
    requests4.append({'createShape': {
        'objectId': f'slide4_ben{i}_title',
        'shapeType': 'TEXT_BOX',
        'elementProperties': {
            'pageObjectId': 'slide4',
            'size': {'width': pt(130), 'height': pt(30)},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(x_offset + 10), 'translateY': pt(160), 'unit': 'PT'}
        }
    }})
    requests4.append({'insertText': {'objectId': f'slide4_ben{i}_title', 'text': f'{{{{benefit_{i}}}}}'}})
    requests4.append({'updateTextStyle': {
        'objectId': f'slide4_ben{i}_title',
        'style': {'foregroundColor': {'opaqueColor': {'rgbColor': DARK}}, 'fontSize': pt(11), 'bold': True},
        'fields': 'foregroundColor,fontSize,bold'
    }})
    # Benefit proof
    requests4.append({'createShape': {
        'objectId': f'slide4_ben{i}_proof',
        'shapeType': 'TEXT_BOX',
        'elementProperties': {
            'pageObjectId': 'slide4',
            'size': {'width': pt(130), 'height': pt(50)},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(x_offset + 10), 'translateY': pt(195), 'unit': 'PT'}
        }
    }})
    requests4.append({'insertText': {'objectId': f'slide4_ben{i}_proof', 'text': f'{{{{proof_{i}}}}}'}})
    requests4.append({'updateTextStyle': {
        'objectId': f'slide4_ben{i}_proof',
        'style': {'foregroundColor': {'opaqueColor': {'rgbColor': GRAY}}, 'fontSize': pt(9), 'italic': True},
        'fields': 'foregroundColor,fontSize,italic'
    }})

slides_service.presentations().batchUpdate(
    presentationId=presentation_id,
    body={'requests': requests4}
).execute()
print('Slide 4 (Why MTP + Benefits) created')

# ============ SLIDE 5: TARIFFS ============
requests5 = []

requests5.append({'createSlide': {
    'objectId': 'slide5',
    'insertionIndex': 4,
    'slideLayoutReference': {'predefinedLayout': 'BLANK'},
}})
requests5.append({'updatePageProperties': {
    'objectId': 'slide5',
    'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': WHITE}}}},
    'fields': 'pageBackgroundFill'
}})

# Section title
requests5.append({'createShape': {
    'objectId': 'slide5_section',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide5',
        'size': {'width': pt(300), 'height': pt(20)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(40), 'unit': 'PT'}
    }
}})
requests5.append({'insertText': {'objectId': 'slide5_section', 'text': 'ТАРИФИ MTP FULFILLMENT'}})
requests5.append({'updateTextStyle': {
    'objectId': 'slide5_section',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': ACCENT}}, 'fontSize': pt(10), 'bold': True},
    'fields': 'foregroundColor,fontSize,bold'
}})

# Tariffs table placeholder
requests5.append({'createTable': {
    'objectId': 'slide5_table',
    'elementProperties': {
        'pageObjectId': 'slide5',
        'size': {'width': pt(420), 'height': pt(200)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(70), 'unit': 'PT'}
    },
    'rows': 8,
    'columns': 2,
}})

# Fill table header
requests5.append({'insertText': {'objectId': 'slide5_table', 'cellLocation': {'rowIndex': 0, 'columnIndex': 0}, 'text': 'Послуга'}})
requests5.append({'insertText': {'objectId': 'slide5_table', 'cellLocation': {'rowIndex': 0, 'columnIndex': 1}, 'text': 'Тариф'}})

# Fill table rows with placeholders
tariff_names = [
    'Прийом товару', 'Зберігання (паллет)', 'Зберігання (коробка)',
    'Комплектація B2C', 'Комплектація B2B', 'Пакування', 'Відправка НП'
]
for i, name in enumerate(tariff_names):
    requests5.append({'insertText': {
        'objectId': 'slide5_table',
        'cellLocation': {'rowIndex': i + 1, 'columnIndex': 0},
        'text': name,
    }})
    requests5.append({'insertText': {
        'objectId': 'slide5_table',
        'cellLocation': {'rowIndex': i + 1, 'columnIndex': 1},
        'text': f'{{{{tariff_{i}}}}}',
    }})

slides_service.presentations().batchUpdate(
    presentationId=presentation_id,
    body={'requests': requests5}
).execute()
print('Slide 5 (Tariffs) created')

# ============ SLIDE 6: PRICING ESTIMATE ============
requests6 = []

requests6.append({'createSlide': {
    'objectId': 'slide6',
    'insertionIndex': 5,
    'slideLayoutReference': {'predefinedLayout': 'BLANK'},
}})
requests6.append({'updatePageProperties': {
    'objectId': 'slide6',
    'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': LIGHT}}}},
    'fields': 'pageBackgroundFill'
}})

requests6.append({'createShape': {
    'objectId': 'slide6_section',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide6',
        'size': {'width': pt(300), 'height': pt(20)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(40), 'unit': 'PT'}
    }
}})
requests6.append({'insertText': {'objectId': 'slide6_section', 'text': 'ОРІЄНТОВНИЙ КОШТОРИС'}})
requests6.append({'updateTextStyle': {
    'objectId': 'slide6_section',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': ACCENT}}, 'fontSize': pt(10), 'bold': True},
    'fields': 'foregroundColor,fontSize,bold'
}})

# Pricing items
pricing_items = ['зберігання_місяць', 'відвантаження_місяць', 'загалом_місяць']
pricing_labels = ['Зберігання / місяць', 'Відвантаження / місяць', 'Загалом / місяць']
for i, (key, label) in enumerate(zip(pricing_items, pricing_labels)):
    y = 80 + i * 60
    # Label
    requests6.append({'createShape': {
        'objectId': f'slide6_price{i}_label',
        'shapeType': 'TEXT_BOX',
        'elementProperties': {
            'pageObjectId': 'slide6',
            'size': {'width': pt(200), 'height': pt(25)},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(y), 'unit': 'PT'}
        }
    }})
    requests6.append({'insertText': {'objectId': f'slide6_price{i}_label', 'text': label}})
    is_total = (i == len(pricing_items) - 1)
    requests6.append({'updateTextStyle': {
        'objectId': f'slide6_price{i}_label',
        'style': {
            'foregroundColor': {'opaqueColor': {'rgbColor': DARK}},
            'fontSize': pt(14 if is_total else 12),
            'bold': is_total,
        },
        'fields': 'foregroundColor,fontSize,bold'
    }})
    # Value
    requests6.append({'createShape': {
        'objectId': f'slide6_price{i}_val',
        'shapeType': 'TEXT_BOX',
        'elementProperties': {
            'pageObjectId': 'slide6',
            'size': {'width': pt(200), 'height': pt(25)},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(280), 'translateY': pt(y), 'unit': 'PT'}
        }
    }})
    requests6.append({'insertText': {'objectId': f'slide6_price{i}_val', 'text': f'{{{{{key}}}}}'}})
    requests6.append({'updateTextStyle': {
        'objectId': f'slide6_price{i}_val',
        'style': {
            'foregroundColor': {'opaqueColor': {'rgbColor': ACCENT if is_total else DARK}},
            'fontSize': pt(16 if is_total else 13),
            'bold': is_total,
        },
        'fields': 'foregroundColor,fontSize,bold'
    }})
    # Divider line
    if not is_total:
        requests6.append({'createLine': {
            'objectId': f'slide6_div{i}',
            'lineCategory': 'STRAIGHT',
            'elementProperties': {
                'pageObjectId': 'slide6',
                'size': {'width': pt(420), 'height': pt(0)},
                'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(60), 'translateY': pt(y + 40), 'unit': 'PT'}
            }
        }})
        requests6.append({'updateLineProperties': {
            'objectId': f'slide6_div{i}',
            'lineProperties': {
                'lineFill': {'solidFill': {'color': {'rgbColor': {'red': 0.88, 'green': 0.89, 'blue': 0.90}}}},
                'weight': pt(1),
            },
            'fields': 'lineFill,weight'
        }})

slides_service.presentations().batchUpdate(
    presentationId=presentation_id,
    body={'requests': requests6}
).execute()
print('Slide 6 (Pricing Estimate) created')

# ============ SLIDE 7: CTA ============
requests7 = []

requests7.append({'createSlide': {
    'objectId': 'slide7',
    'insertionIndex': 6,
    'slideLayoutReference': {'predefinedLayout': 'BLANK'},
}})
requests7.append({'updatePageProperties': {
    'objectId': 'slide7',
    'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': PRIMARY}}}},
    'fields': 'pageBackgroundFill'
}})

# CTA text
requests7.append({'createShape': {
    'objectId': 'slide7_cta',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide7',
        'size': {'width': pt(400), 'height': pt(80)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(100), 'unit': 'PT'}
    }
}})
requests7.append({'insertText': {'objectId': 'slide7_cta', 'text': '{{zoom_cta}}'}})
requests7.append({'updateTextStyle': {
    'objectId': 'slide7_cta',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': WHITE}}, 'fontSize': pt(24), 'bold': True},
    'fields': 'foregroundColor,fontSize,bold'
}})

# Contact info
requests7.append({'createShape': {
    'objectId': 'slide7_contact',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide7',
        'size': {'width': pt(400), 'height': pt(80)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(220), 'unit': 'PT'}
    }
}})
requests7.append({'insertText': {
    'objectId': 'slide7_contact',
    'text': 'mtpgrouppromo@gmail.com\n+38 (050) 144-46-45\nfulfillmentmtp.com.ua\n@nikolay_mtp',
}})
requests7.append({'updateTextStyle': {
    'objectId': 'slide7_contact',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': GRAY}}, 'fontSize': pt(12)},
    'fields': 'foregroundColor,fontSize'
}})

# MTP GROUP footer
requests7.append({'createShape': {
    'objectId': 'slide7_footer',
    'shapeType': 'TEXT_BOX',
    'elementProperties': {
        'pageObjectId': 'slide7',
        'size': {'width': pt(300), 'height': pt(20)},
        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': pt(80), 'translateY': pt(320), 'unit': 'PT'}
    }
}})
requests7.append({'insertText': {'objectId': 'slide7_footer', 'text': 'MTP GROUP — 7+ років на ринку, 60 000+ відправок/місяць'}})
requests7.append({'updateTextStyle': {
    'objectId': 'slide7_footer',
    'style': {'foregroundColor': {'opaqueColor': {'rgbColor': ACCENT}}, 'fontSize': pt(9)},
    'fields': 'foregroundColor,fontSize'
}})

slides_service.presentations().batchUpdate(
    presentationId=presentation_id,
    body={'requests': requests7}
).execute()
print('Slide 7 (CTA) created')

print(f'\n{"="*60}')
print(f'Template ID: {presentation_id}')
print(f'Template URL: https://docs.google.com/presentation/d/{presentation_id}/edit')
print(f'{"="*60}')
