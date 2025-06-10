from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import List, Dict
import uuid
from datetime import datetime
from fastapi import Form, UploadFile, File

import pandas as pd
from scout_agent import classify_items_by_expiry
from logistics_agent import query_food_banks_node, get_best_routes_node
from negotiation_agent import run_negotiation_initial, run_negotiation_step

app = FastAPI()
conversations: Dict[str, Dict] = {}

class BusinessInfo(BaseModel):
    name: str
    type: str
    latitude: float
    longitude: float

class Item(BaseModel):
    food: str
    type: str
    quantity: int
    expiry: str
    
    @field_validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v
    
    @field_validator('expiry')
    def expiry_must_be_valid(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError('Expiry must be in ISO format (YYYY-MM-DD)')
        return v

class StartRequest(BaseModel):
    business_info: BusinessInfo
    inventory: List[Item]

class StartResponse(BaseModel):
    conversation_id: str
    message: str
    status: str

class RespondRequest(BaseModel):
    conversation_id: str
    owner_response: str

class RespondResponse(BaseModel):
    message: str
    status: str

@app.post("/negotiate/start", response_model=StartResponse)
async def negotiate_start(
    business_info: str = Form(...),
    inventory_file: UploadFile = File(...)
):
    try:
        info = BusinessInfo.model_validate_json(business_info)

        if inventory_file.size == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        try:
            raw = pd.read_csv(inventory_file.file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")
        required_columns = ['food_item', 'food_category', 'expiry_date', 'quantity']
        missing_columns = [col for col in required_columns if col not in raw.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )

        df = raw[required_columns].copy()

        df['store_name'] = info.name
        df['todays_date'] = pd.Timestamp.today()

        df['unit'] = 'unit'

        if not all(df['quantity'].apply(lambda x: isinstance(x, (int, float)) and x > 0)):
            raise HTTPException(status_code=400, detail="Invalid quantity values")

        try:
            df['expiry_date'] = pd.to_datetime(df['expiry_date'])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid expiry dates: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    zones = classify_items_by_expiry(df, info.name)
    expiring_df = pd.concat([zones['red_alert'], zones['warning']], ignore_index=True)

    item_list = expiring_df.rename(columns={
        'food_item': 'food',
        'expiry_date': 'expiry'
    })[['food', 'quantity', 'expiry']].to_dict(orient='records')
    state = {
        'lat': info.latitude,
        'lon': info.longitude,
        'expiry_level': 'red_alert' if not zones['red_alert'].empty else 'warning',
        'food_banks': [],
        'routes': []
    }
    state = query_food_banks_node(state)
    state = get_best_routes_node(state)

    conv_state = {
        'business_name': info.name,
        'business_type': info.type,
        'items': item_list,
        'food_banks': state['routes'],
        'previous_attempts': [],
        'current_message': None,
        'response': None,
        'status': 'ongoing'
    }
    conv_state = run_negotiation_initial(conv_state)

    conv_id = str(uuid.uuid4())
    conversations[conv_id] = conv_state
    return StartResponse(
        conversation_id=conv_id,
        message=conv_state['current_message'],
        status=conv_state['status']
    )


@app.post("/negotiate/respond", response_model=RespondResponse)
def negotiate_respond(req: RespondRequest):
    if req.conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    state = conversations[req.conversation_id]
    state = run_negotiation_step(state, req.owner_response)
    
    if state['status'] != 'ongoing':
        del conversations[req.conversation_id]
    else:
        conversations[req.conversation_id] = state

    return RespondResponse(
        message=state.get('current_message', f"Negotiation {state['status']}"),
        status=state['status']
    )

if __name__ == "__main__":
    print("Starting backend server...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)