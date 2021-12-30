
/// Class containing templated methods.
template<typename Value>
class TemplatedClass
{
public:
    /// Template constructor.
    template<typename T>
    TemplatedClass( T &&t );

    /// Variadic template constructor.
    template<typename ...T>
    TemplatedClass( T &&...ts );

    /// Template method.
    template<typename R, typename T1, typename T2>
    R method1( const T1 &t1, const T2 &t2 );

    /// Variadic template method.
    template<typename ...T>
    void method2( T &&...ts );

    /// Variable from template.
    Value value;
};

/// Class containing templated methods.
class NonTemplatedClass
{
public:
    /// Template constructor.
    template<typename T>
    NonTemplatedClass( T &&t );

    /// Variadic template constructor.
    template<typename ...T>
    NonTemplatedClass( T &&...ts );

    /// Template method.
    template<typename R, typename T1, typename T2>
    R method1( const T1 &t1, const T2 &t2 );

    /// Variadic template method.
    template<typename ...T>
    void method2( T &&...ts );

    /// Variable from template.
    Value value;
};
