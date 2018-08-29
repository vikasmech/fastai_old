
        #################################################
        ### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
        #################################################

from nb_003a import *

from itertools import groupby

def closest_ntile(aspect, ntiles):
    return ntiles[np.argmin(abs(log(aspect)-log(ntiles)))]

@dataclass
class SortAspectBatchSampler(Sampler):
    ds:Dataset; bs:int; shuffle:bool = False

    def __post_init__(self):
        asp_ratios = [operator.truediv(*PIL.Image.open(img).size) for img in self.ds.fns]
        asp_ntiles = np.percentile(asp_ratios, [2,20,50,80,98])
        asp_nearests = [closest_ntile(o, asp_ntiles) for o in asp_ratios]
        sort_nearest = sorted(enumerate(asp_nearests), key=itemgetter(1))
        self.groups = [[(a,{'aspect':b}) for a,b in o]
                  for _,o in groupby(sort_nearest, key=itemgetter(1))]
        self.n = sum(math.ceil(len(g)/self.bs) for g in self.groups)

    def __len__(self): return self.n

    def __iter__(self):
        if self.shuffle: groups = [sample(group, len(group)) for group in self.groups]
        else: groups = self.groups
        batches = [group[i:i+self.bs] for group in groups for i in range(0, len(group), self.bs)]
        if self.shuffle: batches = sample(batches, len(batches))
        return iter(batches)

class DatasetTfm(Dataset):
    def __init__(self, ds: Dataset, tfms: Collection[Callable] = None, **kwargs):
        self.ds,self.tfms,self.kwargs = ds,tfms,kwargs

    def __len__(self): return len(self.ds)
    def __getattr__(self, k): return getattr(self.ds, k)

    def __getitem__(self,idx):
        if isinstance(idx, tuple): idx,xtra = idx
        else: xtra={}
        x,y = self.ds[idx]
        return apply_tfms(self.tfms, x, **{**self.kwargs, **xtra}), y

class DataBunch():
    def __init__(self, train_dl, valid_dl, device=None, **kwargs):
        self.device = default_device if device is None else device
        self.train_dl = DeviceDataLoader(train_dl, device=self.device, **kwargs)
        self.valid_dl = DeviceDataLoader(valid_dl, device=self.device, **kwargs)

    @classmethod
    def create(cls, train_ds, valid_ds, bs=64, device=None, num_workers=4, progress_func=tqdm,
               train_tfm=None, valid_tfm=None, sample_func=None, dl_tfms=None, **kwargs):
        if train_tfm is not None: train_tfm = DatasetTfm(train_ds, train_tfm, **kwargs)
        if valid_tfm is not None: valid_tfm = DatasetTfm(valid_ds, valid_tfm, **kwargs)
        if sample_func is None:
            train_dl = DataLoader(train_ds, bs,   shuffle=True,  num_workers=num_workers)
            valid_dl = DataLoader(valid_ds, bs*2, shuffle=False, num_workers=num_workers)
        else:
            train_samp = sample_func(train_ds, bs, True)
            valid_samp = sample_func(valid_ds, bs*2, False)
            train_dl = DataLoader(train_ds, num_workers=num_workers, batch_sampler=train_samp)
            valid_dl = DataLoader(valid_ds, num_workers=num_workers, batch_sampler=valid_samp)
        return cls(train_dl, valid_dl, device, tfms=dl_tfms, progress_func=progress_func)

    @property
    def train_ds(self): return self.train_dl.dl.dataset
    @property
    def valid_ds(self): return self.valid_dl.dl.dataset