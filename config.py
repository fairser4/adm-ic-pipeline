import yaml

def load_config(path="config.yaml"):
  """Read the run configuration from a YAML file into a dict."""
  with open(path) as f:
    cfg = yaml.safe_load(f)
    return cfg

if __name__ == "__main__":
  cfg = load_config()
  print("Loaded config.")