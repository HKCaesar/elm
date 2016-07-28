import contextlib
import inspect

from elm.config import DEFAULTS, ConfigParser, import_callable
from elm.pipeline.tests.util import patch_ensemble_predict
from elm.pipeline.sample_pipeline import check_action_data


EXPECTED_SELECTION_KEYS = ('exclude_polys',
                           'filename_filter',
                           'include_polys',
                           'metadata_filter',
                           'data_filter',
                           'geo_filters')

def expected_fit_kwargs(train_dict):
    fit_kwargs = {
            'get_y_func': train_dict.get('get_y_func'),
            'get_y_kwargs': train_dict.get('get_y_kwargs'),
            'get_weight_func': train_dict.get('get_weight_func'),
            'get_weight_kwargs': train_dict.get('get_weight_kwargs'),
            'batches_per_gen': train_dict['ensemble_kwargs'].get('batches_per_gen'),
            'fit_kwargs': train_dict['fit_kwargs'],
        }
    return fit_kwargs


def test_train_makes_args_kwargs_ok():
    with patch_ensemble_predict() as (elmtrain, elmpredict):
        config = ConfigParser(config=DEFAULTS)
        for step in config.pipeline:
            if 'train' in step:
                break
        train_dict = config.train[step['train']]
        args, kwargs = elmtrain.train_step(config, step, None)
        (executor,
         model_init_class,
         model_init_kwargs,
         fit_args,
         fit_kwargs,
         model_scoring,
         model_scoring_kwargs,
         model_selection_func,
         model_selection_kwargs,) = args
        assert kwargs == train_dict.get('ensemble_kwargs')
        assert executor is None
        assert callable(model_init_class)   # model init func
        assert "KMeans" in repr(model_init_class)
        assert isinstance(model_init_kwargs, dict)  # model init kwargs
        for k,v in train_dict['model_init_kwargs'].items():
            assert model_init_kwargs[k] == v
        # check model init kwargs include the defaults for the method
        defaults = {k: v.default for k,v in inspect.signature(args[1]).parameters.items()}
        for k, v in defaults.items():
            if not k in (set(train_dict['model_init_kwargs']) | {'batch_size'}):
                assert model_init_kwargs.get(k) == v
        # assert fit_func, typically "fit" or "partial_fit"
        # is a method of model_init_class
        check_action_data(fit_args[0])
        # fit_kwargs
        assert fit_kwargs == expected_fit_kwargs(train_dict)
        # model_scoring
        assert not model_scoring or (':' in model_scoring and import_callable(model_scoring))
        # model scoring kwargs

        assert isinstance(model_scoring_kwargs, dict)
        assert not model_selection_func or (':' in model_selection_func and import_callable(model_selection_func))
        assert isinstance(model_selection_kwargs, dict)
        assert model_selection_kwargs.get('model_init_kwargs') == model_init_kwargs
        assert callable(model_selection_kwargs.get('model_init_class'))
