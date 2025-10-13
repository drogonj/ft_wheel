# Reward Functions Configuration

This document provides comprehensive information for configuring and extending the ft_wheel reward system, including available functions and custom development guidelines.

## System Architecture

The ft_wheel reward system employs a modular function loading architecture that dynamically imports reward functions from designated directories:

- **`api/builtins/`**: Core reward functions provided with the system
- **`api/mods/`**: Custom reward functions developed by administrators

Each reward function operates with a paired cancellation function to ensure transaction rollback capabilities. The system performs validation checks during initialization and provides comprehensive error reporting for configuration issues.

### Function Loading Process

The system performs automatic function discovery and validation through these stages:

1. **Path Resolution**: Converts configuration paths to full module references
2. **Dynamic Import**: Loads modules using Python's import system
3. **Function Validation**: Verifies existence of both primary and cancellation functions
4. **Error Handling**: Reports detailed diagnostics for configuration problems

#### Supported Path Formats

Function references in wheel configurations use dot notation for module specification:

```json
{
  "function": "builtins.title",        
  "function": "mods.custom_reward"     
}
```

These paths resolve to complete module references: `api.builtins.title` and `api.mods.custom_reward` respectively.

## Reward Configuration Format

Reward definitions are specified within wheel configuration files located in `backend/django/data/wheel_configs/`. Each reward entry follows this structure:

```json
{
  "sequence": [
    {
      "label": "Reward Name",
      "color": "#FF0000",
      "message": "You won the reward!",
      "function": "builtins.function_name",
      "args": {
        "parameter1": "value1",
        "parameter2": "value2"
      }
    }
  ]
}
```

### Configuration Parameters

| Parameter  | Type   | Description                                      | Required |
| ------------ | -------- | -------------------------------------------------- | ---------- |
| `label`    | string | Display name for the reward segment              | Yes      |
| `color`    | string | Hexadecimal color code for visual representation | Yes      |
| `message`  | string | User notification message upon winning           | Yes      |
| `function` | string | Module path to the reward function               | Yes      |
| `args`     | object | Function-specific parameters                     | No       |

## Available Reward Functions

### Core Functions

#### Default Function (`builtins.default`)

Provides a basic reward implementation for testing and development purposes.

**API Requirements**: None  
**Parameters**: No arguments required

```json
{
  "label": "Test Reward",
  "color": "#808080",
  "message": "You won a test reward!",
  "function": "builtins.default"
}
```

#### Title Assignment (`builtins.title`)

Grants existing 42 Intranet titles to users through the institutional API.

**API Requirements**: Advanced Tutor permissions  
**Parameters**:

| Parameter  | Type | Description                    | Required |
| ------------ | ------ | -------------------------------- | ---------- |
| `title_id` | int  | Existing title identifier      | Yes      |

```json
{
  "label": "Title Award",
  "color": "#800080",
  "message": "You earned a special title!",
  "function": "builtins.title",
  "args": {
    "title_id": 123
  }
}
```

#### Coalition Points (`builtins.coa_points`)

Modifies coalition point balances for user coalitions through the 42 API system.

**API Requirements**: Advanced Staff permissions  
**Template Variables**: `{login}`

| Parameter | Type   | Description                              | Required |
| ----------- | -------- | ------------------------------------------ | ---------- |
| `amount`  | int    | Points modification (positive/negative)  | Yes      |
| `reason`  | string | Transaction description                  | No       |

```json
{
  "label": "Coalition Boost",
  "color": "#FF0000",
  "message": "Your coalition earned bonus points!",
  "function": "builtins.coa_points",
  "args": {
    "amount": 5,
    "reason": "{login} earned bonus coalition points"
  }
}
```

#### Wallet Transactions (`builtins.wallets`)

Processes wallet credit transactions for user accounts through the financial API.

**API Requirements**: Transactions Manager permissions  
**Template Variables**: `{login}`, `{amount}`

| Parameter | Type   | Description                         | Required |
| ----------- | -------- | ------------------------------------- | ---------- |
| `amount`  | int    | Credit modification amount          | Yes      |
| `reason`  | string | Transaction description             | No       |

```json
{
  "label": "Wallet Bonus",
  "color": "#00FF00",
  "message": "Your wallet has been credited!",
  "function": "builtins.wallets",
  "args": {
    "amount": 10,
    "reason": "{login} received {amount} wallet credits"
  }
}
```

#### Exclusive Group Assignment (`builtins.unique_group`)

Manages exclusive group memberships where only one user can hold the group at any time. Automatically transfers ownership from previous holders.

**API Requirements**: Advanced Tutor permissions

| Parameter  | Type | Description                      | Required |
| ------------ | ------ | ---------------------------------- | ---------- |
| `group_id` | int  | Existing group identifier        | Yes      |

```json
{
  "label": "Elite Status",
  "color": "#FFD700",
  "message": "You achieved elite status!",
  "function": "builtins.unique_group",
  "args": {
    "group_id": 561
  }
}
```

#### Community Service Assignment (`builtins.tig`)

Issues community service requirements through the institutional disciplinary system.

**API Requirements**: Basic Staff or Advanced Staff permissions  
**Template Variables**: `{login}`, `{duration}`

| Parameter    | Type   | Description                            | Required |
| -------------- | -------- | ---------------------------------------- | ---------- |
| `duration`   | string | Service duration: "2h", "4h", or "8h" | Yes      |
| `reason`     | string | Assignment justification               | No       |
| `occupation` | string | Service task description               | No       |

```json
{
  "label": "Community Service",
  "color": "#0000FF", 
  "message": "Community service has been assigned.",
  "function": "builtins.tig",
  "args": {
    "duration": "2h",
    "reason": "Wheel assignment for {login}",
    "occupation": "Laboratory maintenance duties"
  }
}
```

## Custom Function Development

Custom reward functions extend system capabilities through modules placed in the `api/mods/` directory. These functions integrate with the same infrastructure as built-in rewards.

### Module Creation

Develop custom functions by creating Python modules in `api/mods/`. Each module must implement both primary and cancellation functions.

```python
def custom_reward(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Custom reward function.
    
    Args:
        api_intra: IntraAPI instance for making API calls
        user: User object with properties like .login, .intra_id, .id
        args: Dictionary of arguments from the reward configuration
        
    Returns:
        tuple: (success: bool, message: str, data: dict)
    """
    
    # Validate arguments
    try:
        required_param = args.get('required_param')
        if not required_param:
            return False, "Missing required_param", {}
    except Exception as e:
        return False, f"Invalid arguments: {e}", {}
    
    # Perform reward logic
    try:
        # Your reward implementation here
        # Use api_intra.request() for API calls
        success, msg, data = api_intra.request('POST', '/v2/endpoint', data={})
        
        if not success:
            return False, f"API call failed: {msg}", data
            
        return True, "Reward granted successfully", data
        
    except Exception as e:
        return False, f"Error granting reward: {e}", {}


def cancel_custom_reward(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Cancel custom reward function.
    
    Args:
        api_intra: IntraAPI instance
        user: User object
        args: Data returned from the original reward function
        
    Returns:
        tuple: (success: bool, message: str, data: dict)
    """
    
    try:
        # Extract cancellation data from original response
        cancel_id = args.get('id')
        if not cancel_id:
            return False, "Missing cancellation ID", {}
        
        # Perform cancellation logic
        success, msg, data = api_intra.request('DELETE', f'/v2/endpoint/{cancel_id}')
        
        return success, msg, data
        
    except Exception as e:
        return False, f"Error canceling reward: {e}", {}
```

### Integration Configuration

Register custom functions in wheel configurations using the `mods` namespace:

```json
{
  "label": "Custom Reward",
  "color": "#FF6B6B",
  "message": "You won a custom reward!",
  "function": "mods.custom_reward",
  "args": {
    "required_param": "value"
  }
}
```

## Function Specification

### Required Function Signatures

All reward functions must implement standardized signatures for system compatibility:

**Primary Function**:
```python
def function_name(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
```

**Cancellation Function**:
```python
def cancel_function_name(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
```

### Parameter Specifications

| Parameter    | Type   | Description                                    |
| -------------- | -------- | ------------------------------------------------ |
| `api_intra`  | object | 42 API interface for institutional operations  |
| `user`       | object | User model with `.login`, `.intra_id`, `.id` |
| `args`       | dict   | Configuration parameters from wheel definition |

### Return Value Structure

Functions must return a three-element tuple containing:

| Element   | Type   | Purpose                                  |
| ----------- | -------- | ------------------------------------------ |
| `success` | bool   | Operation completion status              |
| `message` | string | Human-readable result description        |
| `data`    | dict   | Response data for cancellation reference |

### Template Variable System

String parameters support dynamic replacement variables for personalization and context:

| Variable     | Description                  | Function Availability      |
| -------------- | ------------------------------ | ---------------------------- |
| `{login}`    | User's 42 institutional ID  | Universal                  |
| `{amount}`   | Numerical transaction value  | Wallet and point functions |
| `{duration}` | Time period specification    | Community service function |

#### Usage Example

```json
{
  "args": {
    "reason": "Reward granted to {login} for {amount} credits"
  }
}
```

## Error Management

The system implements comprehensive error handling across multiple operational layers.

### Configuration Errors

| Error Type          | Description                              | Resolution                    |
| --------------------- | ------------------------------------------ | ------------------------------- |
| **Module Import**   | Specified module cannot be loaded       | Verify module path and syntax |
| **Function Missing** | Required function not found in module   | Implement missing functions   |
| **Syntax Errors**   | Module contains Python syntax problems  | Fix code syntax issues        |

### Runtime Error Handling

| Error Category      | Cause                                  | System Response            |
| --------------------- | ---------------------------------------- | ---------------------------- |
| **Validation**      | Invalid or missing required parameters | Return descriptive error   |
| **API Failure**     | 42 Intranet API communication issues  | Log error and return false |
| **Permission**      | Insufficient API access privileges     | Report permission denial   |

### Error Response Protocol

All functions must return standardized error responses:

```python
return False, "Descriptive error message", {}
```

## Configuration Examples

### Coalition Point Rewards

```json
{
  "label": "Coalition Boost",
  "color": "#4ECDC4",
  "message": "Your coalition earned bonus points!",
  "function": "builtins.coa_points",
  "args": {
    "amount": 3,
    "reason": "Wheel victory by {login}"
  }
}
```

### Title Achievement System

```json
{
  "label": "Distinguished Achievement",
  "color": "#9B59B6", 
  "message": "You earned a distinguished title!",
  "function": "builtins.title",
  "args": {
    "title_id": 789
  }
}
```

### Economic Incentives

```json
{
  "label": "Financial Bonus",
  "color": "#2ECC71",
  "message": "Your account has been credited!",
  "function": "builtins.wallets",
  "args": {
    "amount": 15,
    "reason": "Performance bonus for {login}"
  }
}
```

### Disciplinary Actions

```json
{
  "label": "Community Contribution",
  "color": "#E74C3C",
  "message": "Community service assignment received.",
  "function": "builtins.tig",
  "args": {
    "duration": "2h",
    "reason": "Wheel assignment",
    "occupation": "Common area maintenance"
  }
}
```

---

For technical support or questions about implementing custom reward functions, consult the system administrator or refer to the 42 Intranet API documentation for endpoint specifications and required permissions

