# REWARDS OPTIONS

This document explains the reward function system for ft_wheel, including how to configure existing rewards and create custom reward functions.

## Table of Contents

- [Overview](#overview)
- [Auto-Loading Mechanism](#auto-loading-mechanism)
- [Configuration Structure](#configuration-structure)
- [Available Builtin Functions](#available-builtin-functions)
- [Creating Custom Functions](#creating-custom-functions)
- [Function Signature Requirements](#function-signature-requirements)
- [Template Variables](#template-variables)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

The ft_wheel reward system uses an auto-loading mechanism that dynamically imports reward functions from two directories:

- **`api/builtins/`** - Pre-built reward functions provided with the system
- **`api/mods/`** - Custom reward functions created by administrators

Each reward function must have a corresponding cancel function for rollback functionality. The system validates function availability at startup and provides detailed error messages for missing or invalid functions.

## Auto-Loading Mechanism

The reward system automatically loads functions using the following process:

1. **Function Path Resolution**: Converts function paths like `"builtins.default"` to full module paths `"api.builtins.default"`
2. **Module Import**: Dynamically imports the specified module using Python's `importlib`
3. **Function Validation**: Ensures both `function` and `cancel_function` exist and are callable
4. **Error Reporting**: Provides detailed error messages for missing modules or functions

### Supported Path Formats

```json
{
  "function": "builtins.title",        // → api.builtins.title
  "function": "mods.custom_reward"     // → api.mods.custom_reward
}
```

## Configuration Structure

Rewards are configured in JSON files located in `wheel_configs/` with the following structure:

```json
{
  "Reward Name": {
    "color": "#FF0000",
    "number": 3,
    "message": "You won the reward!",
    "function": "builtins.function_name",
    "args": {
      "parameter1": "value1",
      "parameter2": "value2"
    }
  }
}
```

### Configuration Parameters

| Parameter | Type   | Description                                    | Required |
|-----------|--------|------------------------------------------------|----------|
| `color`   | string | Hex color code for UI display                  | Yes      |
| `number`  | int    | Frequency/weight of the reward in the wheel   | Yes      |
| `message` | string | Message displayed to the user upon winning     | Yes      |
| `function`| string | Path to the reward function                    | Yes      |
| `args`    | object | Arguments passed to the reward function        | No       |

## Available Builtin Functions

### 1. Default (`builtins.default`)

Basic reward function for testing and fallback scenarios.

**Arguments**: None required

**Example**:
```json
"Test Reward": {
  "color": "#808080",
  "number": 10,
  "message": "You won a test reward!",
  "function": "builtins.default"
}
```

### 2. Title (`builtins.title`)

Awards an existing 42 Intranet title to the user.

**Required Permissions**: Advanced Tutor

**Arguments**:
- `title_id` (int): ID of the existing title to award

**Example**:
```json
"Title Reward": {
  "color": "#800080",
  "number": 4,
  "message": "You won the title '{title_name}'!",
  "function": "builtins.title",
  "args": {
    "title_id": 123
  }
}
```

### 3. Coalition Points (`builtins.coa_points`)

Adds or removes coalition points from the user's coalition.

**Required Permissions**: Advanced Staff

**Arguments**:
- `amount` (int): Points to add (positive) or remove (negative)
- `reason` (string, optional): Reason for the points change

**Template Variables**: `{login}`

**Example**:
```json
"Coalition Points": {
  "color": "#FF0000",
  "number": 3,
  "message": "You won 5 coalition points!",
  "function": "builtins.coa_points",
  "args": {
    "amount": 5,
    "reason": "{login} won 5 coalition points"
  }
}
```

### 4. Wallets (`builtins.wallets`)

Adds or removes wallet credits from the user's account.

**Required Permissions**: Transactions Manager

**Arguments**:
- `amount` (int): Wallets to add (positive) or remove (negative)
- `reason` (string, optional): Reason for the transaction

**Template Variables**: `{login}`, `{amount}`

**Example**:
```json
"Wallet Reward": {
  "color": "#00FF00",
  "number": 2,
  "message": "You won 10 wallets!",
  "function": "builtins.wallets",
  "args": {
    "amount": 10,
    "reason": "{login} won {amount} wallets"
  }
}
```

### 5. Unique Group (`builtins.unique_group`)

Awards a group that can only be held by one user at a time. When awarded, automatically removes the group from any current holder.

**Required Permissions**: Advanced Tutor

**Arguments**:
- `group_id` (int): ID of the existing group to award

**Example**:
```json
"Unique Group": {
  "color": "#FFD700",
  "number": 1,
  "message": "You won the unique group '{group_name}'!",
  "function": "builtins.unique_group",
  "args": {
    "group_id": 561
  }
}
```

### 6. TIG (Travaux d'Intérêt Général) (`builtins.tig`)

Assigns community service hours to the user.

**Required Permissions**: Basic Staff / Advanced Staff

**Arguments**:
- `duration` (string): Duration of the TIG (`"2h"`, `"4h"`, or `"8h"`)
- `reason` (string, optional): Reason for assigning the TIG
- `occupation` (string, optional): Description of the community service task

**Template Variables**: `{login}`, `{duration}`

**Example**:
```json
"TIG Assignment": {
  "color": "#0000FF",
  "number": 1,
  "message": "You received community service!",
  "function": "builtins.tig",
  "args": {
    "duration": "2h",
    "reason": "{login} won community service",
    "occupation": "Clean the keyboards"
  }
}
```

## Creating Custom Functions

Custom reward functions should be placed in the `api/mods/` directory and follow the established patterns.

### 1. Create Module File

Create a new Python file in `api/mods/` (e.g., `custom_reward.py`):

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

### 2. Configure Custom Reward

Add the custom reward to your wheel configuration:

```json
"Custom Reward": {
  "color": "#FF6B6B",
  "number": 5,
  "message": "You won a custom reward!",
  "function": "mods.custom_reward",
  "args": {
    "required_param": "value"
  }
}
```

## Function Signature Requirements

All reward functions must follow these requirements:

### Function Signature

```python
def function_name(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
```

### Cancel Function Signature

```python
def cancel_function_name(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
```

### Parameters

- **`api_intra`**: IntraAPI instance for making 42 API calls
- **`user`**: User model instance with properties:
  - `.login` - User's 42 login
  - `.intra_id` - User's 42 Intranet ID
  - `.id` - Internal database ID
- **`args`**: Dictionary containing arguments from reward configuration

### Return Value

Both functions must return a tuple with:
- **`success`** (bool): Whether the operation succeeded
- **`message`** (str): Human-readable result message
- **`data`** (dict): Response data (used for cancellation)

## Template Variables

Template variables can be used in string arguments and are automatically replaced:

| Variable     | Description              | Available In           |
|--------------|--------------------------|------------------------|
| `{login}`    | User's 42 login          | All functions          |
| `{amount}`   | Amount value             | `wallets`              |
| `{duration}` | TIG duration             | `tig`                  |

**Example Usage**:
```json
"reason": "{login} won {amount} coalition points on {date}"
```

## Error Handling

The system provides comprehensive error handling:

### Function Loading Errors

- **Module Not Found**: When the specified module doesn't exist
- **Function Not Found**: When the function doesn't exist in the module
- **Import Errors**: When the module has syntax or import errors

### Runtime Errors

- **Validation Errors**: Invalid arguments or missing required parameters
- **API Errors**: Failed 42 Intranet API calls
- **Permission Errors**: Insufficient API permissions

### Error Response Format

```python
return False, "Error message explaining what went wrong", {}
```

## Examples

### Example 1: Simple Points Reward

```json
"Lucky Points": {
  "color": "#4ECDC4",
  "number": 8,
  "message": "You earned bonus coalition points!",
  "function": "builtins.coa_points",
  "args": {
    "amount": 3,
    "reason": "Lucky wheel spin by {login}"
  }
}
```

### Example 2: Title Collection

```json
"Achievement Unlocked": {
  "color": "#9B59B6",
  "number": 2,
  "message": "You unlocked a special achievement!",
  "function": "builtins.title",
  "args": {
    "title_id": 789
  }
}
```

### Example 3: Economic Reward

```json
"Wallet Bonus": {
  "color": "#2ECC71",
  "number": 6,
  "message": "Your wallet has been credited!",
  "function": "builtins.wallets",
  "args": {
    "amount": 15,
    "reason": "Wheel spin reward for {login}"
  }
}
```

### Example 4: Consequence Reward

```json
"Community Service": {
  "color": "#E74C3C",
  "number": 1,
  "message": "Time to contribute to the community!",
  "function": "builtins.tig",
  "args": {
    "duration": "2h",
    "reason": "Wheel spin consequence",
    "occupation": "Organize the common areas"
  }
}
```

---

For technical support or questions about implementing custom reward functions, consult the system administrator or refer to the 42 Intranet API documentation for endpoint specifications and required permissions

