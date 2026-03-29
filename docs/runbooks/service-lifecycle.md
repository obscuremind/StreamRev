# Runbook: Service lifecycle

## Start
```bash
PYTHONPATH=$(pwd) python -m src.service start
```

## Check status
```bash
PYTHONPATH=$(pwd) python -m src.service status
```

## Stop
```bash
PYTHONPATH=$(pwd) python -m src.service stop
```

## Restart
```bash
PYTHONPATH=$(pwd) python -m src.service restart
```

The supervisor stores process metadata in `src/tmp/streamrev-supervisor.json`.


## Heal critical services
```bash
PYTHONPATH=$(pwd) python -m src.service heal
```
