import torch
from torch.autograd import Variable
from gpytorch.math.functions import AddDiag, Invmm
from gpytorch import Distribution

class Kernel(Distribution):
    def initialize(self, **kwargs):
        for param_name, param_value in kwargs.items():
            if hasattr(self, param_name):
                if isinstance(param_value, torch.Tensor):
                    getattr(self, param_name).data.copy_(param_value)
                else:
                    getattr(self, param_name).data.fill_(param_value)
            else:
                raise Exception('%s has no parameter %s' % (self.__class__.__name__, param_name))
        return self


    def forward(self, x1, x2):
        raise NotImplementedError()


    def __call__(self, x1, x2=None):
        if x2 is None:
            x2 = x1
        if x1.data.ndimension() == 1:
            x1 = x1.view(-1, 1)
        if x2.data.ndimension() == 1:
            x2 = x2.view(-1, 1)
        assert(x1.size(1) == x2.size(1))
        return super(Kernel, self).__call__(x1, x2)


class PosteriorKernel(Kernel):
    def __init__(self,kernel,train_x,log_noise=None):
        super(PosteriorKernel, self).__init__()
        self.kernel = kernel
        self.log_noise = log_noise

        # Buffers for conditioning on data
        if isinstance(train_x, Variable):
            train_x = train_x.data
        self.register_buffer('train_x', train_x)


    def forward(self, input):
        train_x_var = Variable(self.train_x)
        test_test_covar = self.kernel(input, input)
        train_test_covar = self.kernel(input, train_x_var)
        
        train_train_covar = self.kernel(train_x_var, train_x_var)
        train_train_covar = AddDiag()(train_train_covar, self.log_noise.exp())

        test_test_covar = test_test_covar.sub(
            torch.mm(train_test_covar, Invmm()(train_train_covar, train_test_covar.t()))
        )

        return test_test_covar


    def __call__(self, x1):
        return Distribution.__call__(self, x1)