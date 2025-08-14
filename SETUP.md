# RL Traffic Control with SUMO-RL - Setup Guide

## 1. System Requirements

### Install SUMO (Eclipse Simulation of Urban MObility)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install sumo sumo-tools sumo-doc
```

**macOS:**
```bash
brew install sumo
```

**Windows:**
- Download from: https://eclipse.org/sumo/
- Add to PATH: `C:\Program Files (x86)\Eclipse\Sumo\bin`

**Verify installation:**
```bash
sumo --version
sumo-gui --version
```

## 2. Install Python packages via UV

### Install UV (if you don't have it)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

### Install all dependencies (including sumo-rl)
```bash
# Go to project directory
cd rl-traffic-control

# Install packages with sumo-rl
uv sync
```

### Alternative - step by step installation
```bash
# Create virtual environment
uv venv

# Activate environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install packages
uv pip install -e .
```

## 3. Create SUMO network

### Create SUMO network automatically
```bash
# Generate basic intersection network (creates sumo/ directory automatically)
uv run python scripts/create_sumo_network.py
```

This creates:
- `sumo/single_intersection.net.xml` - Road network with traffic lights
- `sumo/single_intersection.rou.xml` - Vehicle routes and flows
- `sumo/single_intersection.sumocfg` - SUMO configuration file
- `sumo/gui-settings.cfg` - GUI display settings

## 4. Run training with SUMO-RL

### PPO training (without GUI - faster)
```bash
uv run python scripts/train_ppo.py --num-workers 4 --episodes 500
```

### PPO training with GUI (visualization - slower but visual)
```bash
uv run python scripts/train_ppo.py --gui --num-workers 2 --episodes 100
```

### A3C training (asynchronous advantage actor-critic)
```bash
uv run python scripts/train_a3c.py --num-workers 4 --episodes 500
```

### Training with different reward functions
```bash
# Use queue length minimization
uv run python scripts/train_ppo.py --reward-fn queue --episodes 200

# Use average speed maximization
uv run python scripts/train_ppo.py --reward-fn average-speed --episodes 200

# Use pressure minimization
uv run python scripts/train_ppo.py --reward-fn pressure --episodes 200
```

### Advanced training options
```bash
# Custom action frequency (time between decisions)
uv run python scripts/train_ppo.py --delta-time 10 --episodes 300

# Custom network files
uv run python scripts/train_ppo.py --net-file custom/network.net.xml --route-file custom/routes.rou.xml
```

**Note:** Training will create `ray_results/` directory with checkpoints and logs.

## 5. Model evaluation

### Basic evaluation with GUI
```bash
uv run python scripts/evaluate_rllib.py --checkpoint ray_results/ppo_sumo_rl/PPO_*/checkpoint_000100 --gui --episodes 5
```

### Evaluation without GUI (batch processing)
```bash
uv run python scripts/evaluate_rllib.py --checkpoint ray_results/ppo_sumo_rl/PPO_*/checkpoint_000100 --episodes 10
```

### Compare different reward functions
```bash
# Evaluate with same reward function used in training
uv run python scripts/evaluate_rllib.py --checkpoint ray_results/ppo_sumo_rl/PPO_*/checkpoint_000100 --reward-fn diff-waiting-time --episodes 10

# Test with different reward function
uv run python scripts/evaluate_rllib.py --checkpoint ray_results/ppo_sumo_rl/PPO_*/checkpoint_000100 --reward-fn queue --episodes 10
```

## 6. Demo and testing

### Test SUMO-RL environment
```bash
uv run python scripts/demo_sumo_rl.py --gui --episodes 3
```

### Test without GUI
```bash
uv run python scripts/demo_sumo_rl.py --episodes 5
```

## 7. Available reward functions

SUMO-RL provides several built-in reward functions:

- **diff-waiting-time** (default): Minimizes difference in cumulative waiting time
- **average-speed**: Maximizes average speed of all vehicles  
- **queue**: Minimizes total queue length across intersections
- **pressure**: Minimizes pressure (incoming vs outgoing vehicles difference)

## 8. Results structure

```
ray_results/
├── ppo_sumo_rl/        # PPO results with sumo-rl
├── a3c_sumo_rl/        # A3C results with sumo-rl  
└── ...

experiments/
├── logs/               # Experiment logs
└── results/            # Evaluation results
```

## 9. Monitoring (TensorBoard)

```bash
# Start TensorBoard
uv run tensorboard --logdir ray_results

# Open in browser: http://localhost:6006
```

## 10. Troubleshooting

### SUMO issues
```bash
# Check paths
which sumo
which sumo-gui
echo $SUMO_HOME
```

### SUMO-RL issues
```bash
# Check sumo-rl installation
uv run python -c "import sumo_rl; print(sumo_rl.__version__)"

# Test basic environment creation
uv run python -c "import sumo_rl; env = sumo_rl.env(net_file='sumo/single_intersection.net.xml', route_file='sumo/single_intersection.rou.xml', use_gui=False)"
```

### Ray issues
```bash
# Check Ray
uv run python -c "import ray; print(ray.__version__)"

# Clear Ray cache
ray stop
```

## 11. Multi-agent training (Advanced)

SUMO-RL supports multi-agent environments for complex intersections:

```bash
# Create multi-agent environment (requires custom network with multiple traffic lights)
uv run python scripts/train_multiagent_ppo.py --net-file sumo/grid_network.net.xml
```

## 12. Running experiments

### Compare algorithms
```bash
# PPO
uv run python scripts/train_ppo.py --episodes 500 &

# A3C  
uv run python scripts/train_a3c.py --episodes 500 &

# Wait for completion
wait
```

### Batch evaluation
```bash
# Evaluate all PPO models
for checkpoint in ray_results/ppo_sumo_rl/PPO_*/checkpoint_*; do
    uv run python scripts/evaluate_rllib.py --checkpoint "$checkpoint" --episodes 5
done
```

### Hyperparameter tuning
```bash
# Try different reward functions
for reward in diff-waiting-time queue average-speed pressure; do
    uv run python scripts/train_ppo.py --reward-fn "$reward" --episodes 200 &
done
wait
```

## Quick start (4 commands):

```bash
# 1. Install packages with sumo-rl
uv sync

# 2. Create SUMO network files
uv run python scripts/create_sumo_network.py

# 3. Test SUMO-RL demo (optional)
uv run python scripts/demo_sumo_rl.py --gui --episodes 2

# 4. Start RL training with sumo-rl
uv run python scripts/train_ppo.py --gui --episodes 50
```

## SUMO-RL Advantages

✅ **Pre-built environments**: No need to implement custom TraCI handling  
✅ **Multiple reward functions**: Choose the best for your use case  
✅ **Multi-agent support**: Handle complex intersections  
✅ **Gymnasium compatibility**: Works seamlessly with RL libraries  
✅ **Benchmark networks**: Access to standard traffic scenarios  
✅ **Active development**: Regular updates and bug fixes  

The project now uses the mature sumo-rl library for robust and feature-rich traffic simulation!