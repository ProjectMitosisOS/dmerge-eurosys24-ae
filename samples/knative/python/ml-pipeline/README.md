# Example: Training ML Module

Code from [ML-Pipeline](https://github.com/icanforce/Orion-OSDI22/tree/main/Benchmarks_AWS_Lambda/ML-Pipeline).

Please install all requirements in `requirements.txt`

```shell
pip install -r requirements.txt
```

- `dataset`: MINIST digit dataset
- `full-flow`: Combine all the workflow into one single application `main.py`
  - You can directly run `python main.py` to verify the result.

> NOTE: The training stage takes so long, so this application is not suitable in DMerge.
> 
> But it's helpful to look at the `app.py` to know how to write application in `knative`. Workflow definition file is `service.yaml`, `meta.yaml`, `redis.yaml`